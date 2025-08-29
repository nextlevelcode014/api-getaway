from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from utils.config_dependencies import get_session
from utils.auth_dependencies import verify_admin_key
from utils.billing import (
    send_email,
    render_verify_billing_html,
    render_billing_paid_html,
    render_client_receipt_html,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.billing import send_invoice, get_billings_due_today, generate_receipt_pdf
from sqlalchemy import select
from model.db import async_session, Billing, Client
from datetime import datetime
from schema.schemas import BillingShema, UpdateBillingSchema
from config import ADMIN_EMAIL, RECEIPTS_DIR, BASE_URL, COMPANY_NAME
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


@invoice_router.put("/update/billing", dependencies=[Depends(verify_admin_key)])
async def update_billing(
    data: UpdateBillingSchema, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Billing).where(Billing.id == data.billing_id))
    billing = result.scalars().first()

    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unaivalable")

    billing.due_date = data.due_date
    billing.status = data.status

    session.add(billing)
    await session.commit()
    session.refresh(billing)

    return {"response": "Billing updated successfully"}


async def send_invoice_schedule():
    async with async_session() as session:
        billings = await get_billings_due_today(session)
        for billing in billings:
            await send_invoice(billing, session)


@invoice_router.get("/billing/validate/{pay_hash}")
async def validate_billing_hash(
    pay_hash: str, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Billing).where(Billing.pay_hash == pay_hash))
    billing = result.scalars().first()

    if not billing or billing.status or not billing.pay_hash:
        raise HTTPException(status_code=404, detail="Hash inválida ou expirou")

    return {"response": True}


@invoice_router.post("/pay/{pay_hash}")
async def upload_billing_receipt_secure(
    pay_hash: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Billing)
        .options(selectinload(Billing.client))
        .where(Billing.pay_hash == pay_hash)
    )
    billing = result.scalars().first()
    client = billing.client

    if not billing or billing.status or not billing.pay_hash:
        raise HTTPException(status_code=404, detail="Hash inválida ou expirou")

    client_dir = os.path.join(RECEIPTS_DIR, str(billing.client_id))
    os.makedirs(client_dir, exist_ok=True)

    timestamp = datetime.now().date()
    filename = f"{timestamp}.pdf"
    filepath = os.path.join(client_dir, filename)

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    billing.receipt_file = filepath
    client.active = True

    session.add(billing)
    session.add(client)
    await session.commit()
    await session.refresh(billing)
    await session.refresh(client)

    confirm_url = f"{BASE_URL}/billing/verify/{billing.pay_hash}"
    download_url = f"{BASE_URL}/billing/receipt/{billing.id}"

    template = render_verify_billing_html(billing.client_id, download_url, confirm_url)

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
    result = await session.execute(
        select(Billing)
        .options(selectinload(Billing.client))
        .where(Billing.pay_hash == pay_hash)
    )
    billing = result.scalars().first()

    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unavailable")

    new_billing = Billing(billing.client_id, billing.due_date)

    billing.status = True
    billing.paid_at = datetime.now().date()
    billing.pay_hash = None

    session.add(billing)
    session.add(new_billing)
    await session.commit()
    await session.refresh(billing)

    client = billing.client

    subject = "Pagamento - API Getaway"
    receipt_url = "tste.com"

    template_content = render_billing_paid_html(
        client.name, billing, receipt_url, ADMIN_EMAIL
    )

    await send_email(client.email, subject, template_content)

    return {"response": "Comprovante validado"}


@invoice_router.get("/receipt/{billing_id}")
async def download_receipt(
    billing_id: int, session: AsyncSession = Depends(get_session)
):
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


@invoice_router.get("/client/download/receipt/{billing_id}")
async def client_download_receipt(
    billing_id: str, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Billing)
        .options(selectinload(Billing.client))
        .where(Billing.id == billing_id)
    )
    billing = result.scalars().first()

    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unavailable")

    client = billing.client

    issue_date = datetime.now().date()

    context = {
        "client": {
            "name": client.name,
            "email": client.email,
        },
        "billing": {
            "amount_due": billing.amount_due,
            "paid_at": billing.paid_at,
            "id": billing.id,
        },
        "issue_date": issue_date,
        "company_name": COMPANY_NAME,
    }

    html_template = render_client_receipt_html(
        client, billing, issue_date, COMPANY_NAME
    )

    pdf_bytes = generate_receipt_pdf(
        html_template, context, f"recibo_{context['billing']['id']}.pdf"
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=recibo_{billing_id}.pdf"
        },
    )
