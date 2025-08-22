from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from utils.dependencies import create_session
from model.db import Client
from sqlalchemy.orm import Session
from schema import ClientSchema

admin_router = APIRouter(prefix="/admin", tags=["administration"])


@admin_router.get("/health")
async def health_check():
    return {"status": "admin healthy", "timestamp": datetime.now().isoformat()}


@admin_router.post("/add_client")
async def add_client(
    client_schema: ClientSchema,
    session: Session = Depends(create_session),
):
    client = session.query(Client).filter(Client.email == client_schema.email).first()

    if client:
        raise HTTPException(status_code=400, detail="Unvailable")
    else:
        new_client = Client(
            client_schema.name,
            client_schema.email,
            client_schema.plan,
            client_schema.monthly_limit,
            client_schema.monthly_limit,
        )
        session.add(new_client)
        session.commit()
        return {"message": "Client added successfully"}
