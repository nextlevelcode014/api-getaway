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
)
from sqlalchemy.orm import declarative_base, sessionmaker
import os

os.makedirs("database", exist_ok=True)

db = create_engine("sqlite:///database/sqlite.db")

Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)  # Added unique constraint
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


class ApiKey(Base):
    __tablename__ = "api_key"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client = Column(ForeignKey("clients.id"))
    api_key_hash = Column(String, unique=True, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


# Create all tables
Base.metadata.create_all(db)

# Create session factory
Session = sessionmaker(bind=db)
