from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.admin.routers import admin_router
from app.api.v1.client.routers import client_router
from app.api.v1.payment.routers import payment_router
from app.api.v1.payment.routers import send_invoice_schedule

from contextlib import asynccontextmanager
from app.db.base import init_models

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()

    scheduler.start()
    scheduler.add_job(send_invoice_schedule, CronTrigger(hour=22, minute=59))

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
    }


app.include_router(client_router)
app.include_router(admin_router)
app.include_router(payment_router)
