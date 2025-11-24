from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from auth_service.db.postgres_db import Base


class Workflows(Base):
    __tablename__ = "workflows"

    workflow_id = Column(Integer, primary_key=True,
                         index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    workflow_executions = relationship(
        "WorkflowExecutions", back_populates="workflow")


class WorkflowExecutions(Base):
    __tablename__ = "workflow_executions"

    execution_id = Column(Integer, primary_key=True,
                          index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey(
        "clients.client_id"), nullable=False)
    workflow_id = Column(Integer, ForeignKey(
        "workflows.workflow_id"), nullable=False)
    lead_admin_id = Column(Integer, ForeignKey(
        "lead_admins.lead_admin_id"), nullable=True)
    api_key_id = Column(Integer, ForeignKey(
        "client_api_keys.api_key_id"), nullable=True)
    execution_timestamp = Column(TIMESTAMP, server_default=func.now())
    status = Column(String(50))
    duration_seconds = Column(Integer)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("Clients", back_populates="workflow_executions")
    workflow = relationship("Workflows", back_populates="workflow_executions")
    lead_admin = relationship(
        "LeadAdmins", back_populates="workflow_executions")
    api_key = relationship(
        "ClientAPIKeys", back_populates="workflow_executions")
    credit_entries = relationship(
        "AICreditEntries", back_populates="execution")
    feedback = relationship(
        "Feedback", back_populates="execution", uselist=False)
