from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from auth_service.db.postgres_db import Base


class Clients(Base):
    __tablename__ = "clients"

    client_id = Column(Integer, primary_key=True,
                       index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100))
    website = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    created_by = Column(String(100))
    updated_by = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    lead_admins = relationship("LeadAdmins", back_populates="client")
    api_keys = relationship("ClientAPIKeys", back_populates="client")
    workflow_executions = relationship(
        "WorkflowExecutions", back_populates="client")
    credit_entries = relationship("AICreditEntries", back_populates="client")
    credit_ledger = relationship(
        "AICreditLedger", back_populates="client", uselist=False)
    feedbacks = relationship("Feedback", back_populates="client")

    servers = relationship("ClientServers", back_populates="client")


class LeadAdmins(Base):
    __tablename__ = "lead_admins"

    lead_admin_id = Column(Integer, primary_key=True,
                           index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey(
        "clients.client_id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    created_by = Column(String(100))
    updated_by = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("Clients", back_populates="lead_admins")
    workflow_executions = relationship(
        "WorkflowExecutions", back_populates="lead_admin")


class ClientAPIKeys(Base):
    __tablename__ = "client_api_keys"

    api_key_id = Column(Integer, primary_key=True,
                        index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey(
        "clients.client_id"), nullable=False)
    api_key = Column(String(512), nullable=False, unique=True)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())
    expires_at = Column(TIMESTAMP)
    is_active = Column(Boolean, default=True)
    access_controls = Column(Text)

    # Relationships
    client = relationship("Clients", back_populates="api_keys")
    workflow_executions = relationship(
        "WorkflowExecutions", back_populates="api_key", cascade="all, delete")
