from app.db.model.client import Client
from app.db.model.payment import Billing

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.utils.calculators import calc_billing
from app.utils.generators import generate_qrcode_pix, generate_pay_hash

from app.services.mail.utils.renders import render_invoice_html
from app.services.mail.utils.sender import send_email
from datetime import date

from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from app.api.security import security

from sqlalchemy.orm import selectinload

from app.db.model.client import ClientKey
from app.db.session import get_session


async def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
):
    token = credentials.credentials

    result = await session.execute(
        select(ClientKey)
        .options(selectinload(ClientKey.client_rel))
        .where(ClientKey.client_key_hash == token)
    )
    client_key = result.scalars().first()

    if not client_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client = client_key.client_rel

    if not client or not client.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    return client


async def send_invoice(billing: Billing, session: AsyncSession):
    client = await session.get(Client, billing.client_id)
    client_id = client.id
    data = await calc_billing(client_id, session)

    req_logs = data["req_logs"]
    upload_logs = data["upload_logs"]
    client_amount = data["client_amount"]

    description = "By API Getaway"
    pix_key, qrcode = generate_qrcode_pix(
        client_id, client.name, client_amount, description
    )

    pay_hash = generate_pay_hash()
    pay_url = f"https://nextlevelcodeblog-front.vercel.app/{pay_hash}"

    html_content = render_invoice_html(
        client, req_logs, upload_logs, client_amount, pix_key, pay_url
    )

    client.active = False
    billing.pay_hash = pay_hash
    billing.amount_due = client_amount

    session.add(billing)
    session.add(client)
    await session.commit()
    await session.refresh(billing)
    await session.refresh(client)

    subject = "API Getaway Fatura"

    await send_email(
        client.email,
        subject,
        html_content,
        qrcode,
    )


async def get_billings_due_today(session: AsyncSession):
    today_day = date.today().day
    stmt = select(Billing).where(Billing.due_date == today_day)
    result = await session.execute(stmt)

    return result.scalars().all()
