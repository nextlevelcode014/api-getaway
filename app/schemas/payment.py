from pydantic import BaseModel


class BillingShema(BaseModel):
    client_id: str
    due_date: int


class UpdateBillingSchema(BaseModel):
    billing_id: str
    due_date: int
    status: bool
