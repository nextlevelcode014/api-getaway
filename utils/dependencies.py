from sqlalchemy.orm import sessionmaker
from model.db import db, Client, ClientLog
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import hashlib

import secrets


def create_session():
    try:
        Session = sessionmaker(bind=db)
        session = Session()
        yield session
    finally:
        session.close()


def generate_secure_token():
    return "ak_" + secrets.token_urlsafe(32)


def hash_admin_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def track_usage(session: Session, client_id: int, endpoint: str, tokens_used: int = 1):
    client = session.get(Client, client_id)
    if not client_id:
        return

    now = datetime.now(timezone.utc)

    if client.last_reset.month != now.month or client.last_reset.year != now.year:
        client.used_current_month = 0
        client.last_reset = now

    if client.used_current_month >= client.monthly_limit:
        raise HTTPException(status_code=429, detail="Monthly limit reached")

    client.used_current_month += 1

    log = ClientLog(client.id, endpoint, tokens_used)

    session.add(log)
    session.commit()
