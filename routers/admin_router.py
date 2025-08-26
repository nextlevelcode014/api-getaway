from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from datetime import datetime
from utils.config_dependencies import create_session, generate_secure_token
from utils.auth_dependencies import verify_admin_key
from model.db import Client, ClientKey, Model, ClientUploadLog
from sqlalchemy.orm import Session
import shutil
from pathlib import Path
from decimal import Decimal
from schema.schemas import (
    ClientSchema,
    ModelSchema,
    ClientUpdateSchema,
    AddClientModelSchema,
)
from knowledge_base import create_db, BASE_DIR, VECTOR_DIR
from utils.config_dependencies import (
    calculate_total_upload_cost_gemini,
    calculate_total_upload_cost_openai,
    count_tokens,
)
from config import PRICE_PER_1K_TOKENS, PRICE_PER_1M_TOKENS
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

admin_router = APIRouter(prefix="/admin", tags=["administration"])


@admin_router.get("/health")
async def health_check():
    return {"status": "admin healthy", "timestamp": datetime.now().isoformat()}


@admin_router.post("/add_client", dependencies=[Depends(verify_admin_key)])
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
            client_schema.monthly_limit,
        )
        session.add(new_client)
        session.commit()

        return {"message": "Client added successfully"}


@admin_router.put("/update_client", dependencies=[Depends(verify_admin_key)])
async def update_client(
    client_id: str,
    client_data: ClientUpdateSchema,
    session: Session = Depends(create_session),
):
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


@admin_router.post("/create_client_key", dependencies=[Depends(verify_admin_key)])
async def create_client_key(
    client_id: str,
    session: Session = Depends(create_session),
):
    token = generate_secure_token()
    new_client_key = ClientKey(client_id, token)
    session.add(new_client_key)
    session.commit()

    return {"message": "Client key created successfully"}


@admin_router.post(
    "/add_client_knowledgebase", dependencies=[Depends(verify_admin_key)]
)
async def add_client_knowledgebase(
    client_id: str,
    model: str,
    session: Session = Depends(create_session),
):
    client = session.query(Client).filter(Client.id == client_id, Client.active).first()

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unavailable")

    if not create_db(client.id, model):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong",
        )

    return {"message": "Knowledgebase created successfully"}


@admin_router.post("/revoke_client", dependencies=[Depends(verify_admin_key)])
async def revoke_client(
    client_id: str,
    session: Session = Depends(create_session),
):
    client = session.query(Client).filter(Client.id == client_id, Client.active).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    client.active = False
    client_key = client.keys

    for key in client_key:
        key.active = False

    session.commit()

    return {"message": "Client revoke successfully"}


@admin_router.delete("/delete_client", dependencies=[Depends(verify_admin_key)])
async def delete_client(
    client_id: str,
    session: Session = Depends(create_session),
):
    client = session.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    session.delete(client)
    session.commit()

    return {"message": "Client deleted successfully"}


@admin_router.delete("/delete_client_key", dependencies=[Depends(verify_admin_key)])
async def delete_client_key(
    client_key_id: str,
    session: Session = Depends(create_session),
):
    client_key = (
        session.query(ClientKey)
        .filter(ClientKey.id == client_key_id, Client.active)
        .first()
    )

    if not client_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unaivalable")

    session.delete(client_key)
    session.commit()

    return {"message": "Client Key revoke successfully"}


@admin_router.post("/create_model", dependencies=[Depends(verify_admin_key)])
async def create_model(
    new_model: ModelSchema,
    session: Session = Depends(create_session),
):
    new_model = Model(
        new_model.model_name,
        new_model.token_limit,
        new_model.input_price,
        new_model.output_price,
    )
    session.add(new_model)
    session.commit()

    return {"message": "Model added successfully"}


@admin_router.post("/add_client_model", dependencies=[Depends(verify_admin_key)])
async def add_client_model(
    data: AddClientModelSchema,
    session: Session = Depends(create_session),
):
    client = session.query(Client).filter(Client.id == data.client_id).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
        )

    model = session.query(Model).filter(Model.id == data.client_id).first()

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


@admin_router.delete("/delete_model", dependencies=[Depends(verify_admin_key)])
async def delete_model(
    model_id: str,
    session: Session = Depends(create_session),
):
    model = session.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
        )

    session.delete(model)
    session.commit()

    return {"message": "Model deleted successfully"}


@admin_router.post("/upload_client_pdfs", dependencies=[Depends(verify_admin_key)])
async def upload_client_pdfs(
    client_id: str,
    model: str,
    files: list[UploadFile] = File(...),
    session: Session = Depends(create_session),
):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        )

    client_dir = Path(BASE_DIR) / str(client_id)
    client_dir.mkdir(parents=True, exist_ok=True)

    total_tokens = 0

    for file in files:
        file_path = client_dir / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])

        splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        chunks = splitter.split_text(text)

        for chunk in chunks:
            total_tokens += count_tokens(chunk, model)

    cost = 0

    if model.startswith("gpt-"):
        cost = calculate_total_upload_cost_openai(
            embedding_tokens=total_tokens, price_per_1k_tokens=PRICE_PER_1K_TOKENS
        )
    elif model.startswith("gemini-"):
        cost = calculate_total_upload_cost_gemini(
            embedding_tokens=total_tokens, price_per_1M_tokens=PRICE_PER_1M_TOKENS
        )

    client.upload_tokens += total_tokens
    client.total_upload_cost = (
        Decimal(client.total_upload_cost) or Decimal("0")
    ) + cost

    upload_log = ClientUploadLog(
        embedding_tokens=total_tokens, model_used=model, upload_cost=cost
    )

    session.add(upload_log)

    session.commit()

    create_db(client_id, model)

    return {
        "message": f"{len(files)} files uploaded and knowledge base updated",
        "tokens_indexed": total_tokens,
        "estimated_cost_usd": round(cost, 4),
    }


@admin_router.delete("/delete_client_base", dependencies=[Depends(verify_admin_key)])
async def delete_client_base(
    client_id: str,
    session: Session = Depends(create_session),
):
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
