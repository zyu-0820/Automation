import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.operation_log import OperationLog
from app.models.server import Server
from app.models.service import Service
from app.schemas.operation_log import BatchConfigRequest, OperationLogResponse
from app.services.ssh_service import SSHService

router = APIRouter(tags=["Operations"])


@router.get("/operations", response_model=list[OperationLogResponse])
async def list_operations(
    skip: int = 0,
    limit: int = 50,
    server_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(OperationLog).order_by(OperationLog.created_at.desc()).offset(skip).limit(limit)
    if server_id is not None:
        q = q.where(OperationLog.server_id == server_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/operations/batch/config")
async def batch_update_config(
    body: BatchConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    results = []
    for svc_id in body.service_ids:
        svc_result = await db.execute(select(Service).where(Service.id == svc_id))
        svc = svc_result.scalar()
        if not svc:
            results.append({"service_id": svc_id, "status": "failure", "message": "Service not found"})
            continue

        server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
        server = server_result.scalar()

        try:
            path, backup = await SSHService.write_config_file(
                server, svc.name, body.filename, body.content, body.dir, svc.custom_path
            )
            log = OperationLog(
                server_id=server.id,
                service_id=svc.id,
                operation_type="batch_config",
                target_file=path,
                backup_file=backup,
                status="success",
            )
            db.add(log)
            results.append({
                "service_id": svc_id,
                "server_name": server.name,
                "service_name": svc.name,
                "status": "success",
                "path": path,
            })
        except Exception as e:
            log = OperationLog(
                server_id=server.id,
                service_id=svc.id,
                operation_type="batch_config",
                target_file=body.filename,
                status="failure",
                message=str(e),
            )
            db.add(log)
            results.append({
                "service_id": svc_id,
                "server_name": server.name,
                "service_name": svc.name,
                "status": "failure",
                "message": str(e),
            })

    await db.commit()
    total = len(results)
    success_count = sum(1 for r in results if r["status"] == "success")
    return {"summary": {"total": total, "success": success_count, "failure": total - success_count}, "results": results}


@router.post("/operations/batch/jar")
async def batch_upload_jar(
    file: UploadFile = File(...),
    service_ids: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    import json
    ids = json.loads(service_ids)
    content = await file.read()

    results = []
    for svc_id in ids:
        svc_result = await db.execute(select(Service).where(Service.id == svc_id))
        svc = svc_result.scalar()
        if not svc:
            results.append({"service_id": svc_id, "status": "failure", "message": "Service not found"})
            continue

        server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
        server = server_result.scalar()

        try:
            path, backup = await SSHService.upload_jar(server, svc.name, file.filename, content, svc.custom_path)
            log = OperationLog(
                server_id=server.id,
                service_id=svc.id,
                operation_type="batch_jar",
                target_file=path,
                backup_file=backup,
                status="success",
            )
            db.add(log)
            results.append({
                "service_id": svc_id,
                "server_name": server.name,
                "service_name": svc.name,
                "status": "success",
                "path": path,
                "backup": backup,
            })
        except Exception as e:
            log = OperationLog(
                server_id=server.id,
                service_id=svc.id,
                operation_type="batch_jar",
                target_file=file.filename,
                status="failure",
                message=str(e),
            )
            db.add(log)
            results.append({
                "service_id": svc_id,
                "server_name": server.name,
                "service_name": svc.name,
                "status": "failure",
                "message": str(e),
            })

    await db.commit()
    total = len(results)
    success_count = sum(1 for r in results if r["status"] == "success")
    return {"summary": {"total": total, "success": success_count, "failure": total - success_count}, "results": results}
