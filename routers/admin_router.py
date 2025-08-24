from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from datetime import datetime
from utils.dependencies import create_session, generate_secure_token
from utils.auth_dependencies import verify_admin_key
from model.db import Client, ClientKey, Model
from sqlalchemy.orm import Session
import shutil
from pathlib import Path
from schema import ClientSchema, ModelSchema, ClientUpdateSchema
from knowledge_base import create_db, BASE_DIR, VECTOR_DIR

admin_router = APIRouter(prefix="/admin", tags=["administration"])


@admin_router.get("/health")
async def health_check():
    return {"status": "admin healthy", "timestamp": datetime.now().isoformat()}


@admin_router.post("/add_client")
async def add_client(
    client_schema: ClientSchema,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    client = session.query(Client).filter(Client.email == client_schema.email).first()

    if client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
        )
    else:
        new_client = Client(
            client_schema.name,
            client_schema.email,
            client_schema.monthly_limit,
            client_schema.monthly_limit,
        )
        session.add(new_client)
        session.commit()

        return {"message": "Client added successfully"}


@admin_router.post("/add_client_knowledgebase")
async def add_client_knowledgebase(
    client_id: int,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client = session.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unavailable")

    create_db(client.id)

    return {"message": "Knowledgebase created successfully"}


@admin_router.put("/update_client")
async def update_client(
    client_id: int,
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
    client_id: int,
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
    client_id: int,
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
    client_id: int,
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
    client_key_id: int,
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

    new_model = Model(
        new_model.model_name, new_model.token_limit, new_model.value_per_token
    )
    session.add(new_model)
    session.commit()

    return {"message": "Model added successfully"}


@admin_router.post("/add_client_model")
async def add_client_model(
    client_id: int,
    model_id: int,
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
    model_id: int,
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


@admin_router.post("/upload_client_pdfs")
async def upload_client_pdfs(
    client_id: int,
    files: list[UploadFile] = File(...),
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        )

    client_dir = Path(BASE_DIR) / str(client_id)
    client_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        file_path = client_dir / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

    create_db(client_id)

    return {"message": f"{len(files)} files uploaded and knowledge base updated"}


@admin_router.delete("/delete_client_base")
async def delete_client_base(
    client_id: int,
    session: Session = Depends(create_session),
    admin_key=Depends(verify_admin_key),
):
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        )

    pdf_dir = Path(BASE_DIR) / str(client_id)

    if pdf_dir.exists():
        shutil.rmtree(pdf_dir)

    vector_dir = Path(VECTOR_DIR) / str(client_id)
    if vector_dir.exists():
        shutil.rmtree(vector_dir)

    return {"message": f"All PDFs and knowledge base deleted for client {client_id}"}
