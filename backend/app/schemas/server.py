from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ServerCreate(BaseModel):
    name: str = Field(..., max_length=100)
    host: str
    port: int = Field(default=22, ge=1, le=65535)
    username: str
    auth_type: str = "password"
    password: Optional[str] = None
    private_key: Optional[str] = None
    become_method: str = ""
    become_user: Optional[str] = None
    become_password: Optional[str] = None
    service_base_path: str = "/home/apps/services"
    config_extensions: str = "yml,yaml,xml"


class ServerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    host: Optional[str] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = None
    auth_type: Optional[str] = None
    password: Optional[str] = None
    private_key: Optional[str] = None
    become_method: Optional[str] = None
    become_user: Optional[str] = None
    become_password: Optional[str] = None
    service_base_path: Optional[str] = None
    config_extensions: Optional[str] = None


class ServerResponse(BaseModel):
    id: int
    name: str
    host: str
    port: int
    username: str
    auth_type: str
    become_method: str
    become_user: Optional[str] = None
    service_base_path: str
    config_extensions: str = "yml,yaml,xml"
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ServerWithCredentials(ServerResponse):
    password: Optional[str] = None
    private_key: Optional[str] = None
    become_password: Optional[str] = None
