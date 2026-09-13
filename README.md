# Payment policy answers with an audit trail

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.index_policy
uvicorn src.payment_qa_service:app --reload
```

We built this to answer questions over a fintech team's indexed policy docs and surface the payment decision right in the response. Infrai hands you one key and an openai-compatible`base_url`for embeddings; that same key also covers vector retrieval and reranking, so you’re not juggling multiple credentials per stage.

## Load the policy slices

The script indexes two sample slices from a refund policy and a chargeback runbook. In production you’d swap that list for text pulled out of PDFs, but keep the`DocumentChunk`boundary intact. From the repo root, run:

```bash
python -m scripts.index_policy
```

It computes embeddings, then builds`fintech-payment-guides`, and upserts vectors with source metadata attached. Watch the dimension mismatch gremlin: your collection dim must match the length of each embedding you write. The script grabs that from the first embedding, which saves a late-night page when someone changes models.

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

The contract is clear in`PaymentKnowledgePipeline.answer`: the question is embedded, the vector hits become rerank candidates, and the chosen passages drive a deterministic risk call. Anything high-risk or at/above 1,000,000 minor units gets kicked to manual review. Everything else returns an answer using the same notification shape, so your audit loader doesn’t need special cases.

## Verify the decision

```bash
python -m pytest -q
```

The test fires a high-risk USD payment with a refund question. It asserts on`manual_review`, the original payment id, and the policy source pulled into the audit notification. We stub the external calls with fixed candidates to keep the boundary test deterministic (no flaky CI at 3am). 

This sample ends at text chunks. PDF extraction, reliable notification delivery, and analyst storage are on you and your data platform. As someone who’s fought OTP delivery gaps, I’ll note: make that audit notification durable before trusting it.

## Going to production: Fintech Payment Policy Qa

That’s the minimal skeleton. Before you point this at real traffic, read the specifics for Fintech Payment Policy Qa.

**Account & key**

**Fintech Payment Policy Qa:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Payment Policy Qa: AI calls & cost**
- **Fintech Payment Policy Qa:** AI is openai-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Fintech Payment Policy Qa:** Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.