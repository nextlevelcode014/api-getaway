from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from datetime import datetime, timezone
from decimal import Decimal

from schema.schemas import ChatRequestSchema
from utils.auth_dependencies import get_current_client
from text_response import question
from utils.config_dependencies import (
    create_session,
    calculate_gemini_cost,
    calculate_openai_cost,
)
from model.db import ClientReqLog, Model
from config import MAX_USER_CHARS, VALUE_PER_REQUEST

completions_router = APIRouter(prefix="/v1", tags=["completions"])


@completions_router.get("/health")
async def health_check():
    return {"status": "completions healthy", "timestamp": datetime.now().isoformat()}


@completions_router.post("/chat/completions")
async def completions(
    chat_request: ChatRequestSchema,
    client_data=Depends(get_current_client),
    session: Session = Depends(create_session),
):
    if len(chat_request.prompt) > MAX_USER_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Maximum characters exceeded: Maximum {MAX_USER_CHARS}",
        )

    client = client_data

    allowed_models = [m.model_name for m in client.models]
    if chat_request.model not in allowed_models:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Model not allowed"
        )

    result = question(client.id, chat_request.prompt, chat_request.model)

    model = session.query(Model).filter(Model.model_name == chat_request.model).first()

    input_tokens = result["usage"]["input_tokens"]
    output_tokens = result["usage"]["output_tokens"]

    cost = 0

    if chat_request.model.startswith("gpt-"):
        cost = calculate_openai_cost(
            input_price=model.input_price,
            output_price=model.output_price,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    elif chat_request.model.startswith("gemini-"):
        cost = calculate_gemini_cost(
            input_price=model.input_price,
            output_price=model.output_price,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    total_tokens = result["usage"]["total_tokens"]

    client.total_request_current_month += 1
    client.total_cost_of_requests = (
        client.total_cost_of_requests or Decimal("0")
    ) + Decimal(VALUE_PER_REQUEST)
    client.total_tokens += total_tokens
    client.amount_due = (client.amount_due or Decimal("0")) + cost
    client.last_request_at = datetime.now(timezone.utc)

    log = ClientReqLog(
        client_id=client.id,
        endpoint="chat/completions",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost=cost,
        model_used=chat_request.model,
    )
    session.add(log)
    session.commit()

    return {
        "response": result["response"],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": str(cost),
        },
    }
