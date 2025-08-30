from pydantic import BaseModel


class ModelSchema(BaseModel):
    model_name: str
    token_limit: int
    input_price: float
    output_price: float

    class Config:
        from_attributes = True
