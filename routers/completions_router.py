from fastapi import APIRouter, Depends, HTTPException, status

# from sqlalchemy.orm import Session
# from model.db import Client, ApiKey
# from schema import ApiKeySchema
from datetime import datetime

# from utils.dependencies import verify_api_key
from schema import ChatRequest
from utils.auth_dependencies import get_current_client
from config import OPENAI_API_KEY, OPENAI_BASE_URL

# import hashlib
import time
import httpx

completions_router = APIRouter(prefix="/v1", tags=["completions"])


@completions_router.get("/health")
async def health_check():
    return {"status": "completions healthy", "timestamp": datetime.now().isoformat()}


@completions_router.post("/chat/completions")
async def completions(
    chat_request: ChatRequest, client_data=Depends(get_current_client)
):
    client, token = client_data

    allowed_models = [m.model_name for m in client.models]

    if chat_request.model not in allowed_models:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Model not allowed"
        )

    start_time = time.time()

    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = chat_request.model_dump(exclude_unset=True)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions", headers=headers, json=payload
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OpenAI error: {response.text}",
                )

        durarion = time.time() - start_time

        return response.json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="OpenAI request timeout"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    return {
        "client": client.name,
        "token": token,
        "remaining_requests": client.monthly_limit - client.used_current_month,
    }
