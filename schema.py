from pydantic import BaseModel
from typing import Optional


class ClientSchema(BaseModel):
    name: str
    email: str
    monthly_limit: int

    class Config:
        from_attributes = True


class ModelSchema(BaseModel):
    model_name: str
    token_limit: int
    value_per_token: float


class ClientUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = None
    monthly_limit: Optional[str] = None


class ApiKeySchema(BaseModel):
    client: str
    api_key_hash: str

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    prompt: str
    model: str

    class Config:
        from_attributes = True
