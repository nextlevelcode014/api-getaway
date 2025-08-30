from app.core.config import env
from datetime import datetime


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
