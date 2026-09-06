from src.payment_knowledge import PaymentEvent, PaymentKnowledgePipeline, QuestionRequest


class StubClient:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]

    def query(self, collection: str, embedding: list[float], top_k: int) -> dict:
        return {
            "matches": [
                {
                    "id": "refunds-approval-01",
                    "metadata": {"text": "Refunds above the threshold require analyst approval."},
                }
            ]
        }

    def rerank(self, query: str, candidates: list[str], top_k: int) -> dict:
        return {"results": [{"text": candidates[0], "score": 0.98}]}

    def create_collection(self, collection: str, dimension: int) -> dict:
        return {}

    def upsert(self, collection: str, vectors: list[dict]) -> dict:
        return {}


def test_high_risk_payment_creates_auditable_manual_review() -> None:
    pipeline = PaymentKnowledgePipeline(StubClient())
    request = QuestionRequest(
        question="Can this refund be approved automatically?",
        payment=PaymentEvent(payment_id="pay_2048", amount_minor=250_00, currency="USD", risk_level="high"),
    )

    result = pipeline.answer(request)

    assert result.decision == "manual_review"
    assert result.notification.payment_id == "pay_2048"
    assert result.notification.source_ids == ["refunds-approval-01"]
    assert "analyst approval" in result.answer
