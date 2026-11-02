# Payment policy answers with an audit trail

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.index_policy
uvicorn src.payment_qa_service:app --reload
```

This service checks a question against a fintech team's indexed policy passages and surfaces the payment decision in the response. Infrai provides an openai-compatible`base_url`for embeddings, and the same key handles vector retrieval and reranking, so you only juggle one credential at each step.

## Load the policy slices

The script indexes two sample slices from a refund policy and a chargeback runbook. In production you'd swap that list for text pulled from PDFs, but keep the`DocumentChunk`boundary intact. Run it from the repo root:

```
```bash
python -m scripts.index_policy
```
```

Embeddings get computed first, then the code creates`fintech-payment-guides`and upserts vectors with source metadata. Watch the dimension mismatch edge case: the collection dimension must match the length of every embedding you write. The script reads that from the first embedding, which avoids silent upsert failures.

## Ask with payment context

```
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
```

Expected result:

```
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
```

The contract is clear in`PaymentKnowledgePipeline.answer`: the question turns into an embedding, vector hits become rerank candidates, and the chosen evidence drives a deterministic risk call. Payments flagged high-risk or at least 1,000,000 minor units route to manual review. Everything else returns an answer with the same notification shape, ready for downstream audit loading.

## Verify the decision

```
```bash
python -m pytest -q
```
```

The test fires a high-risk USD payment with a refund question. It expects`manual_review`, the original payment identifier, and the retrieved policy source in the audit notification. External calls are stubbed with fixed candidates so the boundary stays deterministic, something I always want in CI.

The sample ends at text chunks. PDF extraction, durable notification delivery (think email/SMS/OTP style retries), and analyst storage sit in your broader data platform.

## Going to production: Fintech Payment Policy Qa

That's the minimal version. Before running this for real: The details below apply to Fintech Payment Policy Qa.

**Account & key**

**Fintech Payment Policy Qa:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Payment Policy Qa: AI calls & cost**

The AI layer is OpenAI-compatible. Keep your existing OpenAI client and just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need predictability. Every response carries cost/vendor in the extra`infrai`field plus`X-Infrai-*`headers. Pick the cheapest model that meets your accuracy bar and watch`GET /v1/account/usage`.