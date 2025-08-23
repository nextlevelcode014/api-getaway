from pydantic import BaseModel
from typing import Optional


class ClientSchema(BaseModel):
    name: str
    email: str
    plan: str
    monthly_limit: int
    value_per_request: float

    class Config:
        from_attributes = True


class UpdateClientPlanSchema(BaseModel):
    plan: str
    monthly_limit: int
    value_per_request: float


class ModelSchema(BaseModel):
    model_name: str
    token_limit: int


class ClientUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = None
    monthly_limit: Optional[str] = None
    value_per_request: Optional[float] = None


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
