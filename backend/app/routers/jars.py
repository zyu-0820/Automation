import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.operation_log import OperationLog
from app.models.server import Server
from app.models.service import Service
from app.services.ssh_service import SSHService

router = APIRouter(tags=["JARs"])


@router.get("/services/{service_id}/jars")
async def list_jars(service_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
    server = server_result.scalar()

    files = await SSHService.list_jars(server, svc.name, svc.custom_path)
    return files


@router.post("/services/{service_id}/jars/upload")
async def upload_jar(
    service_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.endswith(".jar"):
        raise HTTPException(status_code=400, detail="Only .jar files are allowed")

    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
    server = server_result.scalar()

    content = await file.read()

    try:
        path, backup = await SSHService.upload_jar(server, svc.name, file.filename, content, svc.custom_path)
    except Exception as e:
        log = OperationLog(
            server_id=server.id,
            service_id=svc.id,
            operation_type="jar_upload",
            target_file=file.filename,
            status="failure",
            message=str(e),
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Upload failed: {e}")

    log = OperationLog(
        server_id=server.id,
        service_id=svc.id,
        operation_type="jar_upload",
        target_file=path,
        backup_file=backup,
        status="success",
    )
    db.add(log)
    await db.commit()

    return {"success": True, "path": path, "backup": backup}


@router.delete("/services/{service_id}/jars/{filename}")
async def delete_jar(
    service_id: int,
    filename: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
    server = server_result.scalar()

    await SSHService.delete_jar(server, svc.name, filename, svc.custom_path)

    log = OperationLog(
        server_id=server.id,
        service_id=svc.id,
        operation_type="jar_delete",
        target_file=filename,
        status="success",
    )
    db.add(log)
    await db.commit()

    return {"success": True}
