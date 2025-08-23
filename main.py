from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.completions_router import completions_router
from routers.admin_router import admin_router


app = FastAPI(
    title="Reseller API",
    description="API Gataway para revenda de serviços de AI",
    version="1.0.0",
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
