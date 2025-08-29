from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from utils.config_dependencies import get_session
from utils.auth_dependencies import verify_admin_key
from utils.billing import send_email, render_verify_billing_html
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.billing import send_invoice, get_billings_due_today
from sqlalchemy import select
from model.db import async_session, Billing, Client
from datetime import datetime
from schema.schemas import BillingShema
from config import ADMIN_EMAIL, RECEIPTS_DIR, BASE_URL
import os


invoice_router = APIRouter(prefix="/billing", tags=["billing"])

scheduler = AsyncIOScheduler()

os.makedirs(RECEIPTS_DIR, exist_ok=True)


@invoice_router.post("/send-invoice_manually", dependencies=[Depends(verify_admin_key)])
async def send_invoice_manually(
    client_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Billing).where(Billing.client_id == client_id, ~Billing.status)
    )
    billing = result.scalars().first()

    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unaivaleble")

    await send_invoice(billing, session)

    return {"status": "Invoice sent successfully"}


@invoice_router.post("/issue/billing", dependencies=[Depends(verify_admin_key)])
async def issue_billing(
    data: BillingShema, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Client).where(Client.id == data.client_id))
    client = result.scalars().first()

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unaivalable")

    new_billing = Billing(client.id, data.due_date)

    session.add(new_billing)
    await session.commit()

    return {"response": "Billing issue successfully"}


async def send_invoice_schedule():
    async with async_session() as session:
        billings = await get_billings_due_today(session)
        for billing in billings:
            await send_invoice(billing, session)


@invoice_router.get("/billing/validate/{pay_hash}")
async def validate_billing_hash(pay_hash: str):
    async with async_session() as session:
        result = await session.execute(
            select(Billing).where(Billing.pay_hash == pay_hash)
        )
        billing = result.scalars().first()

        if not billing or billing.status or not billing.pay_hash:
            raise HTTPException(status_code=404, detail="Hash inválida ou expirou")

        return {"response": True}


@invoice_router.post("/billing/pay/{pay_hash}")
async def upload_billing_receipt_secure(
    pay_hash: str,
    file: UploadFile = File(...),
):
    async with async_session() as session:
        result = await session.execute(
            select(Billing).where(Billing.pay_hash == pay_hash)
        )
        billing = result.scalars().first()
        if not billing or billing.status or not billing.pay_hash:
            raise HTTPException(status_code=404, detail="Hash inválida ou expirou")

        client_dir = os.path.join(RECEIPTS_DIR, str(billing.client_id))
        os.makedirs(client_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.pdf"
        filepath = os.path.join(client_dir, filename)

        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)

        billing.receipt_file = filepath

        session.add(billing)
        await session.commit()
        await session.refresh(billing)

        confirm_url = f"{BASE_URL}/billing/verify/{billing.pay_hash}"
        download_url = f"{BASE_URL}/billing/receipt/{billing.id}"

        template = render_verify_billing_html(
            billing.client_id, download_url, confirm_url
        )

        html_content = (
            template.replace("{{client_id}}", str(billing.client_id))
            .replace("{{download_url}}", download_url)
            .replace("{{confirm_url}}", confirm_url)
            .replace("{{amount_due}}", str(billing.amount_due))
        )

        subject = f"Veirificar comprovante do cliente: {billing.client_id}"

        await send_email(ADMIN_EMAIL, subject, html_content)

        return {
            "message": "Comprovante recebido com sucesso",
        }


@invoice_router.get("/verify/{pay_hash}")
async def billing_verify(pay_hash: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Billing).where(Billing.pay_hash == pay_hash))
    billing = result.scalars().first()

    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unaivalable")

    new_billing = Billing(billing.client_id, billing.due_date)

    billing.status = True
    billing.paid_at = datetime.now()
    billing.pay_hash = None

    session.add(billing)
    session.add(new_billing)
    await session.commit()
    await session.refresh(billing)

    return {"response": "Comprovante validado"}


@invoice_router.get("/receipt/{billing_id}")
async def download_receipt(billing_id: int):
    async with async_session() as session:
        result = await session.execute(select(Billing).where(Billing.id == billing_id))
        billing = result.scalars().first()

        if not billing or not billing.receipt_file:
            raise HTTPException(status_code=404, detail="Unaivalable")

        if not os.path.exists(billing.receipt_file):
            raise HTTPException(status_code=404, detail="Unaivalable")

        filename = os.path.basename(billing.receipt_file)
        return FileResponse(
            path=billing.receipt_file, media_type="application/pdf", filename=filename
        )
