from src.infrai_client import InfraiClient
from src.payment_knowledge import DocumentChunk, PaymentKnowledgePipeline


def main() -> None:
    chunks = [
        DocumentChunk(
            chunk_id="refunds-approval-01",
            document_name="refund-policy.pdf",
            text="Refunds above the review threshold require approval from a payments analyst.",
        ),
        DocumentChunk(
            chunk_id="chargeback-evidence-01",
            document_name="chargeback-runbook.pdf",
            text="Chargeback reviews retain the payment identifier and cited policy evidence.",
        ),
    ]
    PaymentKnowledgePipeline(InfraiClient()).index(chunks)
    print(f"Indexed {len(chunks)} payment policy chunks.")


if __name__ == "__main__":
    main()

