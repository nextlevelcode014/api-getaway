from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.completions_router import completions_router
from routers.admin_router import admin_router
from routers.billing_router import invoice_router, send_invoice_schedule

from contextlib import asynccontextmanager
from model.db import init_models

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()

    scheduler.start()
    scheduler.add_job(send_invoice_schedule, CronTrigger(hour=12, minute=46))

    yield
    scheduler.shutdown()


app = FastAPI(
    title="Reseller API",
    description="API Gataway para revenda de serviços de AI",
    version="1.0.0",
    lifespan=lifespan,
)


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
app.include_router(invoice_router)
