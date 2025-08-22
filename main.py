from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from routers.completions_router import completions_router
from routers.admin_router import admin_router

from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

app = FastAPI(
    title="Reseller API",
    description="API Gataway para revenda de serviços de AI",
    version="1.0.0",
)

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer

OPENAI_API_KEY = "sua-chave-openai-aqui"
OPENAI_BASE_URL = "https://api.openai.com/v1"


@app.get("/")
async def root():
    return {
        "service": "AI Reseller API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "stats": "/stats",
            "health": "/health",
        },
    }


app.include_router(completions_router)
app.include_router(admin_router)
