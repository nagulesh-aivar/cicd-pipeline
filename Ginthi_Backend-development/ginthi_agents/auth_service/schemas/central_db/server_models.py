from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from auth_service.db.postgres_db import Base


class ClientServers(Base):
    __tablename__ = "client_servers"

    server_id = Column(Integer, primary_key=True,
                       index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey(
        "clients.client_id"), nullable=False)
    server_name = Column(String(255), nullable=False)
    server_url = Column(String(255))
    server_ip = Column(String(50))
    server_port = Column(Integer)
    server_type = Column(String(50))  # 'Production', 'Staging', 'Development'
    username = Column(String(255))
    password = Column(String(512))  # Store encrypted!
    is_active = Column(Boolean, default=True)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("Clients", back_populates="servers")
