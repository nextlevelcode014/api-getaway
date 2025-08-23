from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from utils.dependencies import create_session, generate_secure_token
from utils.auth_dependencies import verify_admin_key
from model.db import Client, ClientKey, Model
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unvailable"
        )
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


@admin_router.post("/create_client_key")
async def create_client_key(
    client_id: str,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    else:
        token = generate_secure_token()
        new_client_key = ClientKey(client_id, token)
        session.add(new_client_key)
        session.commit()

        return {"message": "Client key created successfully"}


@admin_router.post("/add_model")
async def add_model(
    client_id: str,
    model_name: str,
    token_limit: str,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client = session.query(Client).filter(client_id == Client.id).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unvailable"
        )

    new_client_model = Model(client_id, model_name, token_limit)
    session.add(new_client_model)
    session.commit()

    return {"message": "Client Model added successfully"}
