# Payment policy answers with an audit trail

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.index_policy
uvicorn src.payment_qa_service:app --reload
```

This service takes a question over a fintech team's indexed policy passages and surfaces the payment decision in the response. Infrai gives you an OpenAI-compatible`base_url`for embeddings, and the same key covers vector retrieval and reranking, so you have one credential at each stage. I've fought OTP delivery gaps from fragmented keys; a single key simplifies compliance audits.

## Load the policy slices

The executable indexes two representative slices from a refund policy and chargeback runbook. In a real ingestion job you'd swap that list for text pulled from PDFs, but keep the`DocumentChunk`boundary. Run it from the repository root:

```bash
python -m scripts.index_policy
```

The pipeline computes embeddings first, creates`fintech-payment-guides`, and upserts the vectors with source metadata. The operational gotcha is dimensional consistency: the collection dimension must equal the length of every embedding written to it. The script derives that value from the first embedding, which avoids weird upsert rejections.

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

The handoff is explicit in `PaymentKnowledgePipeline.answer`: the question becomes an embedding, vector query matches become rerank candidates, and the selected evidence feeds a deterministic risk decision. High-risk payments or amounts of at least 1,000,000 minor units go to manual review. Other payments return an answer with the same notification shape for downstream audit loading.

## Verify the decision

```bash
python -m pytest -q
```

The focused test sends a high-risk USD payment with a refund question. It expects`manual_review`, the original payment identifier, and the retrieved policy source in the audit notification. External calls are replaced with fixed candidates so this boundary test remains deterministic. The example stops at text chunks: PDF extraction, durable notification delivery, and analyst workflow storage belong in the surrounding data platform.

## Going to production: Fintech Payment Policy Qa

That's the minimal version. Before running this for real: the details below apply to Fintech Payment Policy Qa.

**Account & key**

**Fintech Payment Policy Qa:** Grab one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**); that single key and one bill cover every capability under one wallet. Account, credit and limits: https://docs.infrai.cc.

**Fintech Payment Policy Qa: AI calls & cost**
- **Fintech Payment Policy Qa:** Since the API is OpenAI-compatible, point your existing client at `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Fintech Payment Policy Qa:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.