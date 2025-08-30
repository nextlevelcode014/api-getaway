from jinja2 import Template
from weasyprint import HTML
from app.core.config import CHAVE_PIX, CIDADE_PIX
from io import BytesIO
import secrets
import hashlib
import qrcode


def generate_pay_hash(length: int = 32) -> str:
    return secrets.token_hex(length // 2)


def generate_secure_token():
    return "ak_" + secrets.token_urlsafe(32)


def hash_admin_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_qrcode_pix(
    client_id: str, name: str, amount_due: float, description: str = ""
):
    payload = generate_payload_pix(amount_due, name, description)
    buffer = BytesIO()
    img = qrcode.make(payload)
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return payload, buffer


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


def generate_receipt_pdf(html_template: str, context: dict, output_path: str):
    template = Template(html_template)
    rendered_html = template.render(context)

    pdf_bytes = HTML(string=rendered_html).write_pdf()

    return pdf_bytes
