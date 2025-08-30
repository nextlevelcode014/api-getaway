from pydantic import BaseModel


class ApiKeySchema(BaseModel):
    client: str
    api_key_hash: str

    class Config:
        from_attributes = True
