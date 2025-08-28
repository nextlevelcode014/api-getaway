from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from datetime import datetime
from utils.config_dependencies import get_session, generate_secure_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from utils.auth_dependencies import verify_admin_key
from model.db import Client, ClientKey, Model, ClientUploadLog
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
from sqlalchemy import select
import aiofiles

admin_router = APIRouter(prefix="/admin", tags=["administration"])


@admin_router.get("/health")
async def health_check():
    return {"status": "admin healthy", "timestamp": datetime.now().isoformat()}


@admin_router.post("/add_client", dependencies=[Depends(verify_admin_key)])
async def add_client(
    client_schema: ClientSchema,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Client).where(Client.email == client_schema.email)
    )
    client = result.scalars().first()

    if client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
        )

    new_client = Client(
        name=client_schema.name,
        email=client_schema.email,
        monthly_limit=client_schema.monthly_limit,
        invoice_due_day=client_schema.invoice_due_day,
    )
    session.add(new_client)
    await session.commit()
    await session.refresh(new_client)

    return new_client


@admin_router.put("/update_client", dependencies=[Depends(verify_admin_key)])
async def update_client(
    client_id: str,
    client_data: ClientUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalars().first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    update_data = client_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(client, key, value)

    await session.commit()
    session.refresh(client)

    return {"response": "Client updated successfully"}


@admin_router.post("/create_client_key", dependencies=[Depends(verify_admin_key)])
async def create_client_key(
    client_id: str,
    session: AsyncSession = Depends(get_session),
):
    token = generate_secure_token()
    new_client_key = ClientKey(client_id, token)
    session.add(new_client_key)
    await session.commit()

    return {"message": "Client key created successfully"}


@admin_router.post(
    "/add_client_knowledgebase", dependencies=[Depends(verify_admin_key)]
)
async def add_client_knowledgebase(
    client_id: str,
    model: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Client).where(Client.id == client_id, Client.active)
    )
    client = result.scalars().first()

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
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Client).where(Client.id == client_id, Client.active)
    )
    client = result.scalars().first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    client.active = False
    client_key = client.keys

    for key in client_key:
        key.active = False

    await session.commit()

    return {"message": "Client revoke successfully"}


@admin_router.delete("/delete_client", dependencies=[Depends(verify_admin_key)])
async def delete_client(
    client_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalars().first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    session.delete(client)
    await session.commit()

    return {"message": "Client deleted successfully"}


@admin_router.delete("/delete_client_key", dependencies=[Depends(verify_admin_key)])
async def delete_client_key(
    client_key_id: str,
    session: AsyncSession = Depends(get_session),
):
    client_key = (
        session.query(ClientKey)
        .filter(ClientKey.id == client_key_id, Client.active)
        .first()
    )

    if not client_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unaivalable")

    session.delete(client_key)
    await session.commit()

    return {"message": "Client Key revoke successfully"}


@admin_router.post("/create_model", dependencies=[Depends(verify_admin_key)])
async def create_model(
    new_model: ModelSchema,
    session: AsyncSession = Depends(get_session),
):
    new_model = Model(
        new_model.model_name,
        new_model.token_limit,
        new_model.input_price,
        new_model.output_price,
    )
    session.add(new_model)
    await session.commit()

    return {"message": "Model added successfully"}


@admin_router.post("/add_client_model", dependencies=[Depends(verify_admin_key)])
async def add_client_model(
    data: AddClientModelSchema,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Client)
        .options(selectinload(Client.models))
        .where(Client.id == data.client_id)
    )
    client = result.scalars().first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
        )

    model = await session.get(Model, data.model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
        )

    if model in client.models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Already linked"
        )

    client.models.append(model)
    session.add(client)
    await session.commit()
    await session.refresh(client)

    return {"message": "Model linked to client successfully"}


@admin_router.delete("/delete_model", dependencies=[Depends(verify_admin_key)])
async def delete_model(
    model_id: str,
    session: AsyncSession = Depends(get_session),
):
    model = await session.get(model_id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unavailable"
        )

    session.delete(model)
    await session.commit()

    return {"message": "Model deleted successfully"}


@admin_router.post("/upload_client_pdfs", dependencies=[Depends(verify_admin_key)])
async def upload_client_pdfs(
    client_id: str,
    model: str,
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
):
    client = await session.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        )

    client_dir = Path(BASE_DIR) / str(client_id)
    client_dir.mkdir(parents=True, exist_ok=True)

    total_tokens = 0

    for file in files:
        file_path = client_dir / file.filename
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])

        splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        chunks = splitter.split_text(text)

        for chunk in chunks:
            total_tokens += count_tokens(chunk, model)

    cost = Decimal("0")
    if model.startswith("gpt-"):
        cost = Decimal(
            calculate_total_upload_cost_openai(total_tokens, PRICE_PER_1K_TOKENS)
        )
    elif model.startswith("gemini-"):
        cost = Decimal(
            calculate_total_upload_cost_gemini(total_tokens, PRICE_PER_1M_TOKENS)
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unaivalable"
        )

    client.upload_tokens += total_tokens
    session.add(client)

    upload_log = ClientUploadLog(
        client_id=client_id,
        embedding_tokens=total_tokens,
        model_used=model,
        upload_cost=cost,
    )
    session.add(upload_log)

    await session.commit()

    create_db(client_id, model)

    return {
        "message": f"{len(files)} files uploaded and knowledge base updated",
        "tokens_indexed": total_tokens,
        "estimated_cost_usd": round(cost, 4),
    }


@admin_router.delete("/delete_client_base", dependencies=[Depends(verify_admin_key)])
async def delete_client_base(
    client_id: str,
    session: AsyncSession = Depends(get_session),
):
    client = await session.get(Client, client_id)
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


@admin_router.get("/client_stats", dependencies=[Depends(verify_admin_key)])
async def client_stats(client_id: str, session: AsyncSession = Depends(get_session)):
    client = await session.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        )

    return {
        "client": client,
    }
