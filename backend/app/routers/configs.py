from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.operation_log import OperationLog
from app.models.server import Server
from app.models.service import Service
from app.services.ssh_service import SSHService

router = APIRouter(tags=["Configs"])


class ConfigContentResponse(BaseModel):
    filename: str
    content: str
    path: str


class ConfigUpdateRequest(BaseModel):
    content: str
    dir: str = "conf"


def _display_path(server: Server, svc: Service) -> str:
    return svc.custom_path or f"{server.service_base_path.rstrip('/')}/{svc.name}"


@router.get("/services/{service_id}/configs")
async def list_config_files(service_id: int, ext: str | None = None, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
    server = server_result.scalar()

    files = await SSHService.list_config_files(server, svc.name, svc.custom_path, ext)
    return files


@router.get("/services/{service_id}/configs/{filename}", response_model=ConfigContentResponse)
async def read_config_file(
    service_id: int,
    filename: str,
    dir: str = Query(default="conf"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
    server = server_result.scalar()

    content = await SSHService.read_config_file(server, svc.name, filename, dir, svc.custom_path)
    path = f"{_display_path(server, svc)}/{dir}/{filename}"
    return ConfigContentResponse(filename=filename, content=content, path=path)


@router.put("/services/{service_id}/configs/{filename}")
async def update_config_file(
    service_id: int,
    filename: str,
    body: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
    server = server_result.scalar()

    try:
        path, backup = await SSHService.write_config_file(
            server, svc.name, filename, body.content, body.dir, svc.custom_path
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    log = OperationLog(
        server_id=server.id,
        service_id=svc.id,
        operation_type="config_edit",
        target_file=path,
        backup_file=backup,
        status="success",
    )
    db.add(log)
    await db.commit()

    return {"success": True, "path": path}
