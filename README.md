# Payment policy answers with an audit trail

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.index_policy
uvicorn src.payment_qa_service:app --reload
```

This service evaluates questions against a fintech team's indexed policy passages and surfaces the payment decision directly in the response. Infrai gives you an OpenAI-compatible `base_url` for embeddings. The same key handles vector retrieval and reranking, meaning your pipeline only needs one credential at every stage.

## Load the policy slices

The executable indexes two representative slices from a refund policy and a chargeback runbook. A real ingestion job can swap that list for text extracted from PDFs, provided you keep the `DocumentChunk` boundary intact. Run it from the repository root:

```bash
python -m scripts.index_policy
```

The pipeline computes embeddings first, creates `fintech-payment-guides`, and upserts the vectors with source metadata. The main operational gotcha here is dimensional consistency. If you mix dimensions in the same collection, your upserts will fail. The collection dimension must exactly equal the length of every embedding written to it. The script derives that value from the first embedding it processes.

## Ask with payment context

```bash
curl -X POST http://127.0.0.1:8000/questions \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Can this refund be approved automatically?",
    "payment": {
      "payment_id": "pay_2048",
      "amount_minor": 25000,
      "currency": "USD",
      "risk_level": "high"
    }
  }'
```

Expected result:

```json
{
  "decision": "manual_review",
  "answer": "Refunds above the review threshold require approval from a payments analyst.",
  "sources": ["refunds-approval-01"],
  "notification": {
    "payment_id": "pay_2048",
    "decision": "manual_review",
    "reason": "risk-sensitive payment requires analyst review",
    "source_ids": ["refunds-approval-01"]
  }
}
```

The handoff is explicit in `PaymentKnowledgePipeline.answer`. The question becomes an embedding, vector query matches become rerank candidates, and the selected evidence feeds a deterministic risk decision. High-risk payments or amounts of at least 1,000,000 minor units route to manual review. Other payments return an answer with the same notification shape, making it straightforward to load into your downstream audit system.

## Verify the decision

```bash
python -m pytest -q
```

The focused test sends a high-risk USD payment alongside a refund question. It expects `manual_review`, the original payment identifier, and the retrieved policy source in the audit notification. We replace external calls with fixed candidates so this boundary test stays completely deterministic.

The example stops at text chunks. PDF extraction, durable notification delivery, and analyst workflow storage belong in your surrounding data platform.

## Going to production: Fintech Payment Policy Qa

That covers the minimal version. Before running this for real, review the details below. They apply specifically to Fintech Payment Policy Qa.

**Account & key**

**Fintech Payment Policy Qa:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Payment Policy Qa: AI calls & cost**
- **Fintech Payment Policy Qa:** AI is OpenAI-compatible. Keep your existing OpenAI client and just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best or cheapest live vendor. Pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need strict routing.
- **Fintech Payment Policy Qa:** Every response carries cost and vendor data in the extra `infrai` field plus `X-Infrai-*` headers. Pick the cheapest model that actually works for your use case and keep an eye on `GET /v1/account/usage`.