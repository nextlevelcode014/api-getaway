from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from datetime import datetime, timezone
from decimal import Decimal

from schema import ChatRequest
from utils.auth_dependencies import get_current_client
from text_response import question
from utils.dependencies import create_session
from model.db import ClientLog, Model
from config import VALUE_PER_REQUEST, MAX_USER_CHARS

completions_router = APIRouter(prefix="/v1", tags=["completions"])


@completions_router.get("/health")
async def health_check():
    return {"status": "completions healthy", "timestamp": datetime.now().isoformat()}


@completions_router.post("/chat/completions")
async def completions(
    chat_request: ChatRequest,
    client_data=Depends(get_current_client),
    session: Session = Depends(create_session),
):
    if len(chat_request.prompt) > MAX_USER_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Maximum characters exceeded: Maximum {MAX_USER_CHARS}",
        )

    client, token = client_data

    allowed_models = [m.model_name for m in client.models]
    if chat_request.model not in allowed_models:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Model not allowed"
        )

    # total tokens used
    result = question(client.id, chat_request.prompt, chat_request.model)

    model = session.query(Model).filter(Model.model_name == chat_request.model).first()

    total_tokens = Decimal(result["usage"]["total_tokens"])
    value_per_token = Decimal(str(model.value_per_token or 0))

    cost = (Decimal(VALUE_PER_REQUEST or 0)) + total_tokens * value_per_token

    client.requests_used += 1
    client.tokens_used += result["usage"]["total_tokens"]
    client.amount_due = (client.amount_due or Decimal("0")) + cost
    client.last_request_at = datetime.now(timezone.utc)

    log = ClientLog(
        client_id=client.id,
        endpoint="chat/completions",
        prompt_tokens=result["usage"]["prompt_tokens"],
        completion_tokens=result["usage"]["completion_tokens"],
        total_tokens=result["usage"]["total_tokens"],
        cost=cost,
    )
    session.add(log)
    session.commit()

    return {
        "response": result["response"],
        "usage": {
            "prompt_tokens": result["usage"]["prompt_tokens"],
            "completion_tokens": result["usage"]["completion_tokens"],
            "total_tokens": total_tokens,
            "cost": str(cost),
        },
    }
