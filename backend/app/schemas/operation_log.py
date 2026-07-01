from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OperationLogResponse(BaseModel):
    id: int
    server_id: Optional[int] = None
    service_id: Optional[int] = None
    operation_type: str
    target_file: Optional[str] = None
    backup_file: Optional[str] = None
    status: str
    message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchConfigRequest(BaseModel):
    service_ids: list[int]
    filename: str
    content: str
    dir: str = "conf"
    mode: str = "overwrite"  # "overwrite" or "append"


class BatchJarRequest(BaseModel):
    service_ids: list[int]
    filename: str
