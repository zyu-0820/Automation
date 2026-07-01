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
    """
    批量更新配置文件到多个服务
    
    该接口接收配置文件内容和一系列服务ID，将配置文件更新到对应服务器上的指定位置，
    并在操作前后记录操作日志，包括成功和失败的情况。
    此功能实现了自动备份机制和语法校验，确保配置更改的安全性。
    
    工作流程：
    1. 遍历每个服务ID，查询对应的服务和服务器信息
    2. 对于每个有效的服务，通过SSH服务将配置文件写入服务器
    3. 在数据库中记录操作日志（成功或失败）
    4. 统计操作结果并返回汇总信息
    
    参数:
        body: 批量配置请求对象，包含服务ID列表、文件名、内容、目录等信息
              - service_ids: 要更新配置的服务ID列表
              - filename: 配置文件名称
              - content: 配置文件内容
              - dir: 目标目录（可选）
        db: 数据库异步会话依赖，用于查询服务/服务器信息和保存操作日志
        
    返回:
        dict: 包含操作汇总统计和详细结果列表的字典
              - summary: 操作汇总统计，包含总数、成功数和失败数
              - results: 详细结果列表，每项包含服务ID、服务器名、服务名、状态和相关信息
    
    异常处理:
        - 如果服务不存在，记录"Service not found"错误
        - 如果SSH操作失败，捕获异常并记录错误消息
        - 所有操作日志都会被持久化到数据库中
    """
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
            if body.mode == "append":
                path, backup = await SSHService.append_config_file(
                    server, svc.name, body.filename, body.content, body.dir, svc.custom_path
                )
            else:
                path, backup = await SSHService.write_config_file(
                    server, svc.name, body.filename, body.content, body.dir, svc.custom_path
                )
            log = OperationLog(
                server_id=server.id,
                service_id=svc.id,
                operation_type="batch_config_append" if body.mode == "append" else "batch_config",
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
    """
    批量上传JAR文件到多个服务
    
    该接口接收一个JAR文件和一系列服务ID，将文件上传到对应服务器上的指定位置，
    并在操作前后记录操作日志，包括成功和失败的情况。
    
    参数:
        file: 上传的JAR文件
        service_ids: 要操作的服务ID列表（JSON格式的字符串）
        db: 数据库异步会话依赖
        
    返回:
        dict: 包含操作汇总统计和详细结果列表的字典
    """
    import json
    # 解析服务ID列表
    ids = json.loads(service_ids)
    # 读取上传文件的内容
    content = await file.read()

    results = []
    # 遍历每个服务ID进行处理
    for svc_id in ids:
        # 查询服务信息
        svc_result = await db.execute(select(Service).where(Service.id == svc_id))
        svc = svc_result.scalar()
        if not svc:
            # 如果服务不存在，记录错误结果并继续下一个
            results.append({"service_id": svc_id, "status": "failure", "message": "Service not found"})
            continue

        # 查询关联的服务器信息
        server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
        server = server_result.scalar()

        try:
            # 通过SSH服务上传JAR文件到服务器
            # 函数返回上传路径和备份文件路径
            path, backup = await SSHService.upload_jar(server, svc.name, file.filename, content, svc.custom_path)
            
            # 创建成功操作日志
            log = OperationLog(
                server_id=server.id,
                service_id=svc.id,
                operation_type="batch_jar",
                target_file=path,
                backup_file=backup,
                status="success",
            )
            db.add(log)
            # 添加成功结果到结果列表
            results.append({
                "service_id": svc_id,
                "server_name": server.name,
                "service_name": svc.name,
                "status": "success",
                "path": path,
                "backup": backup,
            })
        except Exception as e:
            # 如果操作失败，记录失败日志
            log = OperationLog(
                server_id=server.id,
                service_id=svc.id,
                operation_type="batch_jar",
                target_file=file.filename,
                status="failure",
                message=str(e),
            )
            db.add(log)
            # 添加失败结果到结果列表
            results.append({
                "service_id": svc_id,
                "server_name": server.name,
                "service_name": svc.name,
                "status": "failure",
                "message": str(e),
            })

    # 统一提交数据库事务
    await db.commit()
    # 计算操作汇总统计
    total = len(results)
    success_count = sum(1 for r in results if r["status"] == "success")
    # 返回汇总统计和详细结果
    return {"summary": {"total": total, "success": success_count, "failure": total - success_count}, "results": results}
