from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from model.db import Client
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from model.db import ClientReqLog, ClientUploadLog, Billing
from decimal import Decimal, ROUND_HALF_UP
from config import (
    SMTP_FROM_ADDRESS,
    SMTP_PASSWORD,
    SMTP_SERVER,
    SMTP_USERNAME,
)
from config import VALUE_PER_REQUEST, CHAVE_PIX, CIDADE_PIX
import qrcode
import smtplib
import io


env = Environment(loader=FileSystemLoader("templates"))


def render_invoice_html(client, req_logs, upload_logs, total, pix_key):
    template = env.get_template("invoice.html")
    return template.render(
        client=client,
        req_logs=req_logs,
        upload_logs=upload_logs,
        total=total,
        pix_key=pix_key,
        today=datetime.now().strftime("%d/%m/%Y"),
    )


async def get_clients_due_today(session: AsyncSession):
    stmt = select(Client).where(Client.invoice_due_day == date.today())
    result = await session.execute(stmt)

    return result.scalar().all()


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

    return {  # ✅ faltava return
        "req_logs": req_logs,
        "req_cost": req_cost,
        "upload_logs": upload_logs,
        "upload_cost": upload_cost,
        "client_amount": client_amount,
    }


async def send_invoice(client: Client, session: AsyncSession):
    client_id = client.id
    data = await calc_billing(client_id, session)  # ✅ faltava await

    req_logs = data["req_logs"]
    req_cost = data["req_cost"]
    upload_logs = data["upload_logs"]
    upload_cost = data["upload_cost"]
    client_amount = data["client_amount"]

    description = f"Prezado {client.name}, essa cobrança advém dos serviços prestado pela API Getaway."
    pix_key, qrcode = generate_qrcode_pix(
        client_id, client.name, client_amount, description
    )

    html_content = render_invoice_html(
        client,
        req_logs,
        upload_logs,
        client_amount,
        pix_key,
    )

    billing = Billing(client_id, req_cost, upload_cost, client_amount)
    session.add(billing)
    await session.commit()

    msg = MIMEMultipart("related")
    msg["From"] = SMTP_FROM_ADDRESS
    msg["To"] = client.email
    msg["Subject"] = "Sua fatura mensal"

    msg.attach(MIMEText(html_content, "html"))

    if qrcode:
        img_data = qrcode.getvalue()
        image = MIMEImage(img_data)
        image.add_header("Content-ID", "<qrcode>")
        msg.attach(image)

    with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)


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


def generate_payload_pix(amount_due: float, name: str, description: str = "") -> str:
    payload = ""

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
