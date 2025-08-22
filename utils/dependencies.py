from sqlalchemy.orm import sessionmaker
from model.db import db
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
import hashlib

import secrets


def create_session():
    try:
        Session = sessionmaker(bind=db)
        session = Session()
        yield session
    finally:
        session.close()


def generate_api_key():
    return "sk-" + secrets.token_urlsafe(32)


async def verify_api_key(request: Request, session: Session = Depends(create_session)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    api_key = auth_header.split(" ")[1]
    hashed = hashlib.sha256(api_key.encode()).hexdigest()

    client = session.query(Client).filter(Client.email == client_schema.email).first()

    if client:
        raise HTTPException(status_code=400, detail="Unvailable")
    else:
        ...

    # get form database
