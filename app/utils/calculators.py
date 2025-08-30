from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.model.log import RequestLog, UploadLog
from app.core.config import VALUE_PER_REQUEST
from decimal import ROUND_HALF_UP
import tiktoken


def calculate_openai_cost(
    input_price: float, output_price: float, input_tokens: int, output_tokens: int
) -> Decimal:
    """
    input_price/output_price: preço em USD por 1.000 tokens
    input_tokens/output_tokens: número de tokens usados
    """
    cost = (Decimal(input_tokens) / Decimal(1000) * Decimal(input_price)) + (
        Decimal(output_tokens) / Decimal(1000) * Decimal(output_price)
    )
    return cost


def calculate_gemini_cost(
    input_price: float, output_price: float, input_tokens: int, output_tokens: int
) -> Decimal:
    """
    input_price/output_price: preço em USD por 1.000.000 tokens
    input_tokens/output_tokens: número de tokens usados
    """
    input_unit = Decimal(input_price) / Decimal(1_000_000)
    output_unit = Decimal(output_price) / Decimal(1_000_000)

    cost = (Decimal(input_tokens) * input_unit) + (Decimal(output_tokens) * output_unit)
    return cost


def calculate_total_upload_cost_openai(
    embedding_tokens: int, price_per_1k_tokens: float
) -> Decimal:
    """
    embedding_tokens: quantidade de tokens usados para embeddings
    price_per_1k_tokens: preço em USD por 1.000 tokens (OpenAI)
    """
    cost = (Decimal(embedding_tokens) / Decimal(1_000)) * Decimal(price_per_1k_tokens)
    return cost


def calculate_total_upload_cost_gemini(
    embedding_tokens: int, price_per_1M_tokens: float
) -> Decimal:
    """
    embedding_tokens: quantidade de tokens usados para embeddings
    price_per_1M_tokens: preço em USD por 1.000.000 tokens (Gemini)
    """
    cost = (Decimal(embedding_tokens) / Decimal(1_000_000)) * Decimal(
        price_per_1M_tokens
    )
    return cost


def count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    try:
        if "gemini" in model_name.lower:
            return len(text) // 4

        encoding = tiktoken.encoding_for_model(model_name)
        return len(encoding(text))
    except Exception:
        return len(text.split()) * 1.3


async def calc_billing(client_id: str, session: AsyncSession):
    req_logs = (
        (
            await session.execute(
                select(RequestLog).where(RequestLog.client_id == client_id)
            )
        )
        .scalars()
        .all()
    )

    upload_logs = (
        (
            await session.execute(
                select(UploadLog).where(UploadLog.client_id == client_id)
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
