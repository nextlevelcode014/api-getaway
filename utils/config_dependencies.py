from sqlalchemy.ext.asyncio import AsyncSession
from model.db import async_session
from decimal import Decimal
from typing import AsyncGenerator
import tiktoken
import hashlib

import secrets


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def generate_secure_token():
    return "ak_" + secrets.token_urlsafe(32)


def hash_admin_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


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
