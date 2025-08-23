from sqlalchemy.orm import sessionmaker
from model.db import db
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
