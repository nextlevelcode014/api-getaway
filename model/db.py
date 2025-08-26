from sqlalchemy import (
    create_engine,
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
from sqlalchemy.orm import declarative_base, relationship
import os

os.makedirs("database", exist_ok=True)

db = create_engine("sqlite:///database/sqlite.db")

Base = declarative_base()


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
    models = relationship("Model", secondary=client_models, back_populates="clients")
    monthly_limit = Column(Float, default=2000)
    total_cost_of_requests = Column(Numeric(precision=18, scale=6), default=0)
    total_request_current_month = Column(Integer, default=0)
    amount_due = Column(Numeric(precision=12, scale=2), default=0)
    total_tokens = Column(Float, default=0)
    upload_tokens = Column(Float, default=0)
    total_upload_cost = Column(Numeric(precision=12, scale=2), default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_reset = Column(DateTime, server_default=func.now())

    def __init__(
        self,
        name,
        email,
        monthly_limit,
    ):
        self.name = name
        self.email = email
        self.monthly_limit = monthly_limit


class ClientReqLog(Base):
    __tablename__ = "client_req_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))
    endpoint = Column(String, nullable=True)
    input_tokens = Column(Float, nullable=True)
    output_tokens = Column(Float, nullable=True)
    total_token_used = Column(Float, nullable=True)
    model_used = Column(String, nullable=True)
    cost = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", backref="logs")

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


class ClientUploadLog(Base):
    __tablename__ = "client_upload_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_cost = Column(Numeric(precision=12, scale=2), default=0)
    embedding_tokens = Column(Float, default=0)
    model_used = Column(String, nullable=True)

    def __init__(self, upload_cost, embedding_tokens, model_used):
        self.upload_cost = upload_cost
        self.embedding_tokens = embedding_tokens
        self.model_used = model_used


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String, nullable=False, unique=True)
    clients = relationship("Client", secondary=client_models, back_populates="models")
    token_limit = Column(Integer, nullable=True)
    input_price = Column(Numeric(precision=12, scale=2), default=0)
    output_price = Column(Numeric(precision=12, scale=2), default=0)

    def __init__(self, model_name, token_limit, input_price, output_price):
        self.model_name = model_name
        self.token_limit = token_limit
        self.input_price = input_price
        self.output_price = output_price


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


Base.metadata.create_all(db)
