from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from utils.config_dependencies import get_session
from utils.auth_dependencies import verify_admin_key
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.billing import send_invoice, get_clients_due_today
from model.db import Client
import asyncio


invoice_router = APIRouter(prefix="/billing", tags=["billing"])

scheduler = AsyncIOScheduler()


@invoice_router.post("/send-invoice_manually", dependencies=[Depends(verify_admin_key)])
async def send_invoice_manually(
    client_id: int,
    session: AsyncSession = Depends(get_session),
):
    client = await session.get(Client, client_id)

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unaivaleble")

    await send_invoice(client, session)

    return {"status": "Invoice sent successfully"}


@invoice_router.post("/send-invoice-schedule")
async def send_invoice_schedule(session: AsyncSession = Depends(get_session)):
    clients = await get_clients_due_today(session)

    for client in clients:
        asyncio.create_task(send_invoice(client, session))
