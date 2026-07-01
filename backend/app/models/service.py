from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

from app.database import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    display_name = Column(String(200), nullable=True)
    custom_path = Column(String(500), nullable=True)
    control_method = Column(String(20), nullable=False, default="auto")
    status = Column(String(20), default="unknown")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("server_id", "name", name="uq_server_service"),)
