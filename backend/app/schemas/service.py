from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ServiceCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    custom_path: Optional[str] = None
    control_method: str = "auto"


class ServiceUpdate(BaseModel):
    display_name: Optional[str] = None
    custom_path: Optional[str] = None
    control_method: Optional[str] = None


class ServiceResponse(BaseModel):
    id: int
    server_id: int
    name: str
    display_name: Optional[str] = None
    custom_path: Optional[str] = None
    control_method: str = "auto"
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ServiceScanRequest(BaseModel):
    pass


class ServiceScanResponse(BaseModel):
    found: list[str]
    added: list[str]
    existing: list[str]
