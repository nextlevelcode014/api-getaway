from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from config import ADMIN_API_KEY
from model.db import ClientKey
from utils.dependencies import create_session
from security import security


async def verify_admin_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    print(ADMIN_API_KEY)
    if credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    return True


async def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(create_session),
):
    token = credentials.credentials
    client_key = (
        session.query(ClientKey)
        .filter(ClientKey.client_key_hash == token, ClientKey.active == True)
        .first()
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

    if client.used_current_month >= client.monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite mensal excedido ({client.monthly_limit} requests)",
        )

    return client, token
