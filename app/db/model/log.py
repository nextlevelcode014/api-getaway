from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    func,
    ForeignKey,
    Numeric,
)
from sqlalchemy.orm import relationship
from app.db.base import Base

from decimal import Decimal


class RequestLog(Base):
    __tablename__ = "client_req_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))
    clients = relationship("Client", back_populates="client_req_logs")
    endpoint = Column(String, nullable=True)
    input_tokens = Column(Float, nullable=True)
    output_tokens = Column(Float, nullable=True)
    total_token_used = Column(Float, nullable=True)
    model_used = Column(String, nullable=True)
    cost = Column(
        Numeric(precision=12, scale=6), nullable=True, default=Decimal("0.00")
    )

    created_at = Column(DateTime, server_default=func.now())

    def __init__(
        self,
        client_id,
        endpoint,
        input_tokens,
        output_tokens,
        total_tokens,
        model_used,
        cost,
    ):
        self.client_id = client_id
        self.endpoint = endpoint
        self.total_token_used = total_tokens
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cost = cost
        self.model_used = model_used


class UploadLog(Base):
    __tablename__ = "client_upload_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))
    clients = relationship("Client", back_populates="client_upload_logs")
    upload_cost = Column(
        Numeric(precision=12, scale=6), nullable=True, default=Decimal("0.00")
    )
    embedding_tokens = Column(Float, default=0)
    model_used = Column(String, nullable=True)

    def __init__(self, client_id, upload_cost, embedding_tokens, model_used):
        self.client_id = client_id
        self.upload_cost = upload_cost
        self.embedding_tokens = embedding_tokens
        self.model_used = model_used
