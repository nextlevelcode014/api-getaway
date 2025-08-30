from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from typing import Optional

from app.core.config import (
    SMTP_FROM_ADDRESS,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_USERNAME,
)

import smtplib


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
