from pydantic import BaseModel


class ClientSchema(BaseModel):
    name: str
    email: str
    plan: str
    monthly_limit: int
    value_per_request: float

    class Config:
        from_attributes = True


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
