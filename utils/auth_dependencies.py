from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from config import ADMIN_API_KEY
from model.db import ClientKey
from utils.config_dependencies import create_session
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
    session: Session = Depends(create_session),
):
    token = credentials.credentials
    client_key = (
        session.query(ClientKey).filter(ClientKey.client_key_hash == token).first()
    )

    if not client_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client = client_key.client_rel

    if not client or not client.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    if client.total_tokens >= client.monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly limit reached ({client.monthly_limit} tokens)",
        )

    return client
