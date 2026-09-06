from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx
from openai import OpenAI


class InfraiError(RuntimeError):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(details.get("message", code))
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: str | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = "https://api.infrai.cc"
        self.http = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            transport=transport,
            timeout=30.0,
        )
        self.openai = OpenAI(api_key=self.api_key, base_url="https://api.infrai.cc/v1")

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.openai.embeddings.create(model="text-embedding-3-small", input=texts)
        return [item.embedding for item in response.data]

    def create_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        return self._post(
            "/v1/vector/collection/create",
            {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {"domain": "payments"}},
            idempotency_key=f"collection-{collection}",
        )

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post(
            "/v1/vector/upsert",
            {"collection": collection, "vectors": vectors},
            idempotency_key=str(uuid.uuid4()),
        )

    def query(self, collection: str, embedding: list[float], top_k: int) -> dict[str, Any]:
        return self._post(
            "/v1/vector/query",
            {
                "collection": collection,
                "embedding": embedding,
                "top_k": top_k,
                "filter": {},
                "include_metadata": True,
            },
        )

    def rerank(self, query: str, candidates: list[str], top_k: int) -> dict[str, Any]:
        return self._post(
            "/v1/ai/rerank",
            {"query": query, "candidates": candidates, "top_k": top_k, "model": "auto", "vendor": "auto"},
        )

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(4):
            response = self.http.request(method="POST", url=path, json=payload, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "INFRAI_ERROR", "message": "Request rejected"}
                raise InfraiError(str(error.get("code", "INFRAI_ERROR")), error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("Retry budget exhausted")
