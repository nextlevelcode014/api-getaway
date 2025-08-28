from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from decimal import Decimal

from schema.schemas import ChatRequestSchema
from utils.auth_dependencies import get_current_client
from text_response import question
from utils.config_dependencies import (
    get_session,
    calculate_gemini_cost,
    calculate_openai_cost,
)
from model.db import ClientReqLog, Model, Client
from config import MAX_USER_CHARS

completions_router = APIRouter(prefix="/v1", tags=["completions"])


@completions_router.get("/health")
async def health_check():
    return {"status": "completions healthy", "timestamp": datetime.now().isoformat()}


@completions_router.post("/chat/completions")
async def completions(
    chat_request: ChatRequestSchema,
    client: Client = Depends(get_current_client),
    session: AsyncSession = Depends(get_session),
):
    if len(chat_request.prompt) > MAX_USER_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Maximum characters exceeded: Maximum {MAX_USER_CHARS}",
        )

    await session.refresh(client, attribute_names=["models"])
    allowed_models = [m.model_name for m in client.models]

    if chat_request.model not in allowed_models:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Model not allowed"
        )

    question_result = question(client.id, chat_request.prompt, chat_request.model)
    usage = question_result["usage"]
    response_text = question_result["response"]

    result = await session.execute(
        select(Model).where(Model.model_name == chat_request.model)
    )
    model = result.scalars().first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Model not found"
        )

    input_tokens = usage["input_tokens"]
    output_tokens = usage["output_tokens"]
    total_tokens = usage["total_tokens"]

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
    else:
        cost = Decimal("0")

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

    await session.commit()
    await session.refresh(log)

    return {
        "response": response_text,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": str(cost),
        },
    }
