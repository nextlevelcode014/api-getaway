from fastapi import APIRouter, Depends
from datetime import datetime
from utils.dependencies import verify_api_key

completions_router = APIRouter(prefix="/v1", tags=["completions"])


@completions_router.get("/health")
async def health_check():
    return {"status": "completions healthy", "timestamp": datetime.now().isoformat()}


@completions_router.get("/chat/completions")
async def completions(prompt: str, client=Depends(verify_api_key)): ...
