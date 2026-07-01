from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.server import Server
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceResponse, ServiceScanResponse, ServiceUpdate
from app.services.ssh_service import SSHService

router = APIRouter(tags=["Services"])


@router.get("/servers/{server_id}/services", response_model=list[ServiceResponse])
async def list_services(server_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Service).where(Service.server_id == server_id).order_by(Service.name)
    )
    return result.scalars().all()


@router.post("/servers/{server_id}/services", response_model=ServiceResponse, status_code=201)
async def create_service(server_id: int, body: ServiceCreate, db: AsyncSession = Depends(get_db)):
    server_result = await db.execute(select(Server).where(Server.id == server_id))
    if not server_result.scalar():
        raise HTTPException(status_code=404, detail="Server not found")

    existing = await db.execute(
        select(Service).where(Service.server_id == server_id, Service.name == body.name)
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Service name already exists on this server")

    svc = Service(server_id=server_id, name=body.name, custom_path=body.custom_path or None)
    db.add(svc)
    await db.commit()
    await db.refresh(svc)
    return svc


@router.post("/servers/{server_id}/services/scan", response_model=ServiceScanResponse)
async def scan_services(server_id: int, db: AsyncSession = Depends(get_db)):
    server_result = await db.execute(select(Server).where(Server.id == server_id))
    server = server_result.scalar()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    existing_result = await db.execute(
        select(Service).where(Service.server_id == server_id)
    )
    existing_names = {s.name for s in existing_result.scalars().all()}

    found_names = await SSHService.scan_services(server)

    added = []
    for name in found_names:
        if name not in existing_names:
            svc = Service(server_id=server_id, name=name)
            db.add(svc)
            added.append(name)

    await db.commit()
    return ServiceScanResponse(
        found=found_names,
        added=added,
        existing=[n for n in found_names if n in existing_names],
    )


@router.get("/services/{service_id}", response_model=ServiceResponse)
async def get_service(service_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    return svc


@router.put("/services/{service_id}", response_model=ServiceResponse)
async def update_service(service_id: int, body: ServiceUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(svc, key, value)

    await db.commit()
    await db.refresh(svc)
    return svc


@router.delete("/services/{service_id}", status_code=204)
async def delete_service(service_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    await db.delete(svc)
    await db.commit()


@router.post("/services/{service_id}/refresh-status", response_model=ServiceResponse)
async def refresh_status(service_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
    server = server_result.scalar()

    svc.status = await SSHService.get_service_status(server, svc.name)
    await db.commit()
    await db.refresh(svc)
    return svc


@router.post("/servers/{server_id}/services/refresh-all")
async def refresh_all_status(server_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Service).where(Service.server_id == server_id)
    )
    services = result.scalars().all()

    server_result = await db.execute(select(Server).where(Server.id == server_id))
    server = server_result.scalar()

    updated = []
    for svc in services:
        svc.status = await SSHService.get_service_status(server, svc.name)
        updated.append({"id": svc.id, "status": svc.status})

    await db.commit()
    return {"updated": updated}


@router.post("/services/{service_id}/start")
async def start_service(service_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
    server = server_result.scalar()

    success, message = await SSHService.start_service(server, svc.name, svc.custom_path, svc.control_method)
    return {"success": success, "message": message}


@router.post("/services/{service_id}/stop")
async def stop_service(service_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
    server = server_result.scalar()

    success, message = await SSHService.stop_service(server, svc.name, svc.custom_path, svc.control_method)
    return {"success": success, "message": message}


@router.post("/services/{service_id}/restart")
async def restart_service(service_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    server_result = await db.execute(select(Server).where(Server.id == svc.server_id))
    server = server_result.scalar()

    success, message = await SSHService.restart_service(server, svc.name, svc.custom_path, svc.control_method)
    return {"success": success, "message": message}
