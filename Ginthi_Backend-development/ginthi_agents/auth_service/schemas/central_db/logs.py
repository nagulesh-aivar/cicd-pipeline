# auth_service/schemas/central_db/logs.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, Float, DateTime, func
from auth_service.db.postgres_db import Base  # ← your SQLAlchemy Base

class TransactionLog(Base):
    __tablename__ = "transaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(100), default="anonymous")
    ip = Column(String(50))
    method = Column(String(10))
    path = Column(String(255))
    status_code = Column(Integer)
    duration_ms = Column(Float)
    headers = Column(JSON, nullable=True)
    request_body = Column(JSON, nullable=True)
    response_body = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now()) 
    service_name = Column(String(100), nullable=True)  
