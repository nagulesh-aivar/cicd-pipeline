from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, Text, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from auth_service.db.postgres_db import Base


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id = Column(Integer, primary_key=True,
                         index=True, autoincrement=True)
    execution_id = Column(Integer, ForeignKey(
        "workflow_executions.execution_id"), nullable=False)
    client_id = Column(Integer, ForeignKey(
        "clients.client_id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comments = Column(Text)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    execution = relationship("WorkflowExecutions", back_populates="feedback")
    client = relationship("Clients", back_populates="feedbacks")
