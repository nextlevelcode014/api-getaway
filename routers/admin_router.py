from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from utils.dependencies import create_session, generate_secure_token
from utils.auth_dependencies import verify_admin_key
from model.db import Client, ClientKey, Model
from sqlalchemy.orm import Session
from schema import ClientSchema, ModelSchema, ClientUpdateSchema

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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
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


@admin_router.put("/update_client")
async def update_client(
    client_id: str,
    client_data: ClientUpdateSchema,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client = session.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    update_data = client_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(client, key, value)

    session.commit()
    session.refresh(client)

    return {"response": "Client updated successfully"}


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


@admin_router.post("/revoke_client")
async def revoke_client(
    client_id: str,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client = session.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    if not client.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    client.active = False
    client_key = client.keys

    for key in client_key:
        key.active = False

    session.commit()

    return {"message": "Client revoke successfully"}


@admin_router.delete("/delete_client")
async def delete_client(
    client_id: str,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client = session.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    if not client.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    session.delete(client)

    session.commit()

    return {"message": "Client deleted successfully"}


@admin_router.delete("/delete_client_key")
async def delete_client_key(
    client_key_id: str,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client_key = session.query(ClientKey).filter(ClientKey.id == client_key_id).first()

    if not client_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unaivalable")

    if not client_key.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unaivalable")

    session.delete(client_key)

    session.commit()

    return {"message": "Client Key revoke successfully"}


@admin_router.post("/create_model")
async def create_model(
    new_model: ModelSchema,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    new_model = Model(new_model.model_name, new_model.token_limit)
    session.add(new_model)
    session.commit()

    return {"message": "Model added successfully"}


@admin_router.post("/add_client_model")
async def add_client_model(
    client_id: str,
    model_id: str,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client = session.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
        )

    model = session.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
        )

    if model in client.models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unavailable",
        )

    client.models.append(model)
    session.commit()

    return {"message": "Model linked to client successfully"}


@admin_router.delete("/delete_model")
async def delete_model(
    model_id: str,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    model = session.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
        )

    session.delete(model)

    session.commit()

    return {"message": "Model deleted successfully"}
