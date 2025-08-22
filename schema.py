class ClientSchema:
    name: str
    email: str
    plan: str
    monthly_limit: int
    value_per_request: float

    class Config:
        from_attributes = True
