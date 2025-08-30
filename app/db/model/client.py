from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Float,
    DateTime,
    func,
    ForeignKey,
    Table,
    Numeric,
)
from app.db.base import Base


from sqlalchemy.orm import relationship
from decimal import Decimal

client_models = Table(
    "client_models",
    Base.metadata,
    Column("client_id", Integer, ForeignKey("clients.id"), primary_key=True),
    Column("model_id", Integer, ForeignKey("models.id"), primary_key=True),
)


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    keys = relationship(
        "ClientKey",
        back_populates="client_rel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    models = relationship(
        "Model",
        secondary=client_models,
        back_populates="clients",
    )
    client_req_logs = relationship(
        "RequestLog", cascade="all, delete-orphan", back_populates="clients"
    )
    client_upload_logs = relationship(
        "UploadLog", cascade="all, delete-orphan", back_populates="clients"
    )
    monthly_limit = Column(Float, default=2000)
    cost = Column(
        Numeric(precision=12, scale=6), nullable=True, default=Decimal("0.00")
    )
    upload_tokens = Column(Float, default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_reset = Column(DateTime, server_default=func.now())

    def __init__(self, name, email, monthly_limit):
        self.name = name
        self.email = email
        self.monthly_limit = monthly_limit


class ClientKey(Base):
    __tablename__ = "client_keys"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=True)
    client = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))
    client_key_hash = Column(String, nullable=True, unique=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    client_rel = relationship("Client", back_populates="keys")

    def __init__(self, client_id, client_key_hash):
        self.client = client_id
        self.client_key_hash = client_key_hash
