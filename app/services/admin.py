from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from app.api.security import security

from app.core.config import ADMIN_API_KEY


async def verify_admin_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
