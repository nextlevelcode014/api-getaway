from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from model.db import ClientReqLog, ClientUploadLog, Billing, Client
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from config import (
    SMTP_FROM_ADDRESS,
    SMTP_PASSWORD,
    SMTP_SERVER,
    SMTP_USERNAME,
)
from config import VALUE_PER_REQUEST, CHAVE_PIX, CIDADE_PIX, SMTP_PORT, env
from weasyprint import HTML
from jinja2 import Template
import qrcode
import smtplib
import io
import uuid
import secrets


def generate_billing_hash() -> str:
    return uuid.uuid4().hex


def generate_pay_hash(length: int = 32) -> str:
    return secrets.token_hex(length // 2)


def render_invoice_html(client, req_logs, upload_logs, total, pix_key, pay_url):
    template = env.get_template("invoice.html")
    return template.render(
        client=client,
        req_logs=req_logs,
        upload_logs=upload_logs,
        total=total,
        pix_key=pix_key,
        today=datetime.now().date(),
        pay_url=pay_url,
    )


def render_verify_billing_html(client_id, download_url, confirm_url):
    template = env.get_template("verify_billing.html")
    return template.render(
        client_id=client_id,
        download_url=download_url,
        confirm_url=confirm_url,
    )


def render_billing_paid_html(client_name, billing, receipt_url, support_email):
    template = env.get_template("billing_paid.html")
    return template.render(
        client_name=client_name,
        billing=billing,
        receipt_url=receipt_url,
        support_email=support_email,
    )


def render_client_receipt_html(client, billing, issue_date, company_name):
    template = env.get_template("receipt.html")
    return template.render(
        client=client,
        billing=billing,
        issue_date=issue_date,
        company_name=company_name,
    )


async def get_billings_due_today(session: AsyncSession):
    today_day = date.today().day
    stmt = select(Billing).where(Billing.due_date == today_day)
    result = await session.execute(stmt)

    return result.scalars().all()


async def calc_billing(client_id: str, session: AsyncSession):
    req_logs = (
        (
            await session.execute(
                select(ClientReqLog).where(ClientReqLog.client_id == client_id)
            )
        )
        .scalars()
        .all()
    )

    upload_logs = (
        (
            await session.execute(
                select(ClientUploadLog).where(ClientUploadLog.client_id == client_id)
            )
        )
        .scalars()
        .all()
    )

    req_cost = Decimal("0.00")
    total_reqs = Decimal("0.00")
    for log in req_logs:
        total_reqs += VALUE_PER_REQUEST
        req_cost += log.cost

    upload_cost = Decimal("0.00")
    for log in upload_logs:
        upload_cost += log.upload_cost

    client_amount = req_cost + upload_cost + total_reqs
    client_amount = client_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "req_logs": req_logs,
        "req_cost": req_cost,
        "upload_logs": upload_logs,
        "upload_cost": upload_cost,
        "client_amount": client_amount,
    }


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


def crc16(data: bytes) -> str:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if (crc & 0x8000) != 0:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    qrcode: Optional[bytes] = None,
    attachments: Optional[list[tuple[str, bytes]]] = None,
):
    msg = MIMEMultipart("related")
    msg["From"] = SMTP_FROM_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(html_content, "html"))

    if qrcode:
        image = MIMEImage(qrcode.getvalue())
        image.add_header("Content-ID", "<qrcode>")
        msg.attach(image)

    if attachments:
        for filename, file_bytes in attachments:
            part = (
                MIMEImage(file_bytes)
                if filename.endswith((".png", ".jpg", ".jpeg"))
                else MIMEText(file_bytes.decode("utf-8"), "plain")
            )
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)


def generate_payload_pix(amount_due: float, name: str, description: str = "") -> str:
    payload = ""
    amount_due = 2.0

    payload += "000201"

    payload += "010211"

    gui = "br.gov.bcb.pix"
    conta = f"0014{gui}01{len(CHAVE_PIX):02}{CHAVE_PIX}"
    if description:
        conta += f"02{len(description):02}{description}"
    payload += f"26{len(conta):02}{conta}"

    payload += "52040000"
    payload += "5303986"
    if amount_due > 0:
        payload += f"54{len(f'{amount_due:.2f}'):02}{amount_due:.2f}"

    payload += "5802BR"
    payload += f"59{len(name):02}{name}"
    payload += f"60{len(CIDADE_PIX):02}{CIDADE_PIX}"

    add_data = "05" + f"{len('***'):02}***"
    payload += f"62{len(add_data):02}{add_data}"

    payload += "6304"
    payload += crc16(payload.encode("utf-8"))

    return payload


def generate_qrcode_pix(
    client_id: str, name: str, amount_due: float, description: str = ""
):
    payload = generate_payload_pix(amount_due, name, description)
    buffer = io.BytesIO()
    img = qrcode.make(payload)
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return payload, buffer


def generate_receipt_pdf(html_template: str, context: dict, output_path: str):
    template = Template(html_template)
    rendered_html = template.render(context)

    pdf_bytes = HTML(string=rendered_html).write_pdf()

    return pdf_bytes
