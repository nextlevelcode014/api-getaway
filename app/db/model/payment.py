from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    func,
    ForeignKey,
    Numeric,
)
from sqlalchemy.orm import relationship

from decimal import Decimal


from app.db.base import Base


class Billing(Base):
    __tablename__ = "billings"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    client_id = Column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    client = relationship("Client")
    receipt_file = Column(String, unique=True, nullable=True)

    pay_hash = Column(String(64), unique=True, index=True, nullable=True)

    amount_due = Column(Numeric(12, 6), nullable=True, default=Decimal("0.00"))

    status = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(Integer, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    def __init__(
        self,
        client: str,
        due_date: int = None,
    ):
        self.client_id = client
        self.due_date = due_date

    def __repr__(self):
        return f"<Billing id={self.id} client={self.client} due={self.due_date} status={self.status}>"
