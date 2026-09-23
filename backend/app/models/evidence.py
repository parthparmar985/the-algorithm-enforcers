from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, UniqueConstraint
from ..database.database import Base


class Investigation(Base):
    __tablename__ = "investigations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vehicle_plate = Column(String(50), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (UniqueConstraint("investigation_id", "source_key", name="uq_evidence_source"),)
    id = Column(Integer, primary_key=True)
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False, index=True)
    evidence_type = Column(String(30), nullable=False)
    source_key = Column(String(80), nullable=False)
    detection_id = Column(Integer, nullable=True)
    vehicle_id = Column(Integer, nullable=True)
    alert_id = Column(Integer, nullable=True)
    camera_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    vehicle_plate = Column(String(50), index=True)
    file_path = Column(String(500), nullable=True)
    sha256 = Column(String(64), nullable=True)
    description = Column(Text, nullable=False, default="")
    details = Column(JSON, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
