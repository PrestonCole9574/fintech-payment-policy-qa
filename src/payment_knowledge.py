from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

class PaymentEvent(BaseModel):
    payment_id: str = Field(min_length=1)
    amount_minor: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    risk_level: Literal["low", "medium", "high"]


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3)
    payment: PaymentEvent


class AuditNotification(BaseModel):
    payment_id: str
    decision: Literal["answer", "manual_review"]
    reason: str
    source_ids: list[str]


class QuestionResult(BaseModel):
    decision: Literal["answer", "manual_review"]
    answer: str
    sources: list[str]
    notification: AuditNotification


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    text: str
    document_name: str


class PaymentKnowledgePipeline:
    def __init__(self, client: Any, collection: str = "fintech-payment-guides") -> None:
        self.client = client
        self.collection = collection

    def index(self, chunks: list[DocumentChunk]) -> None:
        embeddings = self.client.embed([chunk.text for chunk in chunks])
        if not embeddings:
            return
        self.client.create_collection(self.collection, len(embeddings[0]))
        vectors = [
            {
                "id": chunk.chunk_id,
                "values": embedding,
                "metadata": {"text": chunk.text, "document_name": chunk.document_name},
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        self.client.upsert(self.collection, vectors)

    def answer(self, request: QuestionRequest) -> QuestionResult:
        question_embedding = self.client.embed([request.question])[0]
        query_data = self.client.query(self.collection, question_embedding, top_k=8)
        matches = query_data.get("matches", [])
        candidates = [str(match.get("metadata", {}).get("text", "")) for match in matches]
        candidates = [text for text in candidates if text]
        reranked = self.client.rerank(request.question, candidates, top_k=min(3, len(candidates))) if candidates else {}
        passages = self._ranked_passages(reranked, candidates)
        source_ids = [str(match.get("id")) for match in matches[: len(passages)]]

        needs_review = request.payment.risk_level == "high" or request.payment.amount_minor >= 1_000_000
        decision: Literal["answer", "manual_review"] = "manual_review" if needs_review else "answer"
        reason = "risk-sensitive payment requires analyst review" if needs_review else "policy evidence retrieved"
        answer = passages[0] if passages else "No matching policy passage was retrieved."
        notification = AuditNotification(
            payment_id=request.payment.payment_id,
            decision=decision,
            reason=reason,
            source_ids=source_ids,
        )
        return QuestionResult(decision=decision, answer=answer, sources=source_ids, notification=notification)

    @staticmethod
    def _ranked_passages(reranked: dict[str, Any], fallback: list[str]) -> list[str]:
        results = reranked.get("results", [])
        ranked = [str(item.get("text", "")) for item in results if item.get("text")]
        return ranked or fallback[:3]
