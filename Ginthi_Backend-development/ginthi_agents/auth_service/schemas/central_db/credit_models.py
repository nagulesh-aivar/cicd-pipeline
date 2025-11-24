from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from auth_service.db.postgres_db import Base


class AICreditLedger(Base):
    __tablename__ = "ai_credit_ledger"

    client_id = Column(Integer, ForeignKey(
        "clients.client_id"), primary_key=True)
    current_balance = Column(Integer, nullable=False, default=0)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    last_updated = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("Clients", back_populates="credit_ledger")


class AICreditEntries(Base):
    __tablename__ = "ai_credit_entries"

    credit_entry_id = Column(Integer, primary_key=True,
                             index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey(
        "clients.client_id"), nullable=False)
    execution_id = Column(Integer, ForeignKey(
        "workflow_executions.execution_id"), nullable=True)
    # Positive for credits added, negative for credits used
    change_amount = Column(Integer, nullable=False)
    reason = Column(String(255))
    created_by = Column(String(100))
    updated_by = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    client = relationship("Clients", back_populates="credit_entries")
    execution = relationship("WorkflowExecutions",
                             back_populates="credit_entries")
