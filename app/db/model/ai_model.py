from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
)
from sqlalchemy.orm import relationship
from app.db.model.client import client_models
from decimal import Decimal
from app.db.base import Base


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String, nullable=False, unique=True)
    clients = relationship("Client", secondary=client_models, back_populates="models")
    token_limit = Column(Integer, nullable=True)
    input_price = Column(
        Numeric(precision=12, scale=6), nullable=True, default=Decimal("0.00")
    )
    output_price = Column(
        Numeric(precision=12, scale=6), nullable=True, default=Decimal("0.00")
    )

    def __init__(self, model_name, token_limit, input_price, output_price):
        self.model_name = model_name
        self.token_limit = token_limit
        self.input_price = input_price
        self.output_price = output_price
