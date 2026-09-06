from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .payment_knowledge import PaymentKnowledgePipeline, QuestionRequest, QuestionResult

app = FastAPI(title="Payment policy question service")


@app.post("/questions", response_model=QuestionResult)
def answer_payment_question(request: QuestionRequest) -> QuestionResult:
    try:
        return PaymentKnowledgePipeline(InfraiClient()).answer(request)
    except InfraiError as error:
        status_code = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail={"code": error.code, "message": str(error)}) from error

