from pydantic import BaseModel
from typing import Optional


class ClientSchema(BaseModel):
    name: str
    email: str
    monthly_limit: int

    class Config:
        from_attributes = True


class ClientUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = None
    monthly_limit: Optional[str] = None

    class Config:
        from_attributes = True


class ChatRequestSchema(BaseModel):
    prompt: str
    model: str

    class Config:
        from_attributes = True


class AddClientModelSchema(BaseModel):
    model_id: str
    client_id: str
