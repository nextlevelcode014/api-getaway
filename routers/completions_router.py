from fastapi import APIRouter, Depends, HTTPException, status

from datetime import datetime

from schema import ChatRequest
from utils.auth_dependencies import get_current_client
from text_response import question


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

    text_response = question(chat_request.prompt, chat_request.model)
    return {"response": text_response}
