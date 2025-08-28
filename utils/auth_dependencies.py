from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from config import ADMIN_API_KEY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from model.db import ClientKey
from utils.config_dependencies import get_session
from security import security


async def verify_admin_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )


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
