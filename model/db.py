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
    email = Column(String, nullable=False, unique=True)  # Added unique constraint
    models = relationship("Model", back_populates="client")
    plan = Column(String, default="normal")
    monthly_limit = Column(Integer, default=1000)
    used_current_month = Column(Integer, default=0)
    value_per_request = Column(Float, default=0.01)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_reset = Column(DateTime, server_default=func.now())

    def __init__(
        self, name, email, plan=None, monthly_limit=None, value_per_request=None
    ):
        self.name = name
        self.email = email
        if plan is not None:
            self.plan = plan
        if monthly_limit is not None:
            self.monthly_limit = monthly_limit
        if value_per_request is not None:
            self.value_per_request = value_per_request

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.name}', email='{self.email}')>"


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    model_name = Column(String, nullable=False)
    client = relationship("Client", back_populates="models")
    token_limit = Column(Integer, nullable=True)

    def __init__(self, client_id, model_name, token_limit):
        self.client_id = client_id
        self.model_name = model_name
        self.token_limit = token_limit


class ClientKey(Base):
    __tablename__ = "client_keys"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=True)
    client = Column(ForeignKey("clients.id"))
    client_key_hash = Column(String, nullable=True, unique=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    client_rel = relationship("Client", backref="keys")

    def __init__(self, client_id, client_key_hash):
        self.client = client_id
        self.client_key_hash = client_key_hash


Base.metadata.create_all(db)
