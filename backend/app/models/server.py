from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database import Base


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=22)
    username = Column(String(100), nullable=False)
    auth_type = Column(String(20), nullable=False, default="password")
    encrypted_password = Column(Text, nullable=True)
    encrypted_private_key = Column(Text, nullable=True)
    become_method = Column(String(20), nullable=False, default="")
    become_user = Column(String(100), nullable=True)
    encrypted_become_password = Column(Text, nullable=True)
    service_base_path = Column(String(500), nullable=False, default="/home/apps/services")
    config_extensions = Column(String(200), nullable=False, default="yml,yaml,xml")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
