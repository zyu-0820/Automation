from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.server import Server
from app.models.service import Service
from app.routers.services import router as services_sub_router
from app.schemas.server import ServerCreate, ServerResponse, ServerUpdate
from app.services.ssh_service import SSHService
from app.utils.encryption import encrypt

router = APIRouter(tags=["Servers"])


@router.get("/servers", response_model=list[ServerResponse])
async def list_servers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Server).order_by(Server.name))
    return result.scalars().all()


@router.post("/servers", response_model=ServerResponse, status_code=201)
async def create_server(body: ServerCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Server).where(Server.name == body.name))
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Server name already exists")

    server = Server(
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
        auth_type=body.auth_type,
        become_method=body.become_method or "",
        become_user=body.become_user,
        service_base_path=body.service_base_path,
        config_extensions=body.config_extensions or "yml,yaml,xml",
    )
    if body.auth_type == "password" and body.password:
        server.encrypted_password = encrypt(body.password)
    elif body.auth_type == "key" and body.private_key:
        server.encrypted_private_key = encrypt(body.private_key)
    if body.become_password:
        server.encrypted_become_password = encrypt(body.become_password)

    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


@router.get("/servers/{server_id}", response_model=ServerResponse)
async def get_server(server_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.put("/servers/{server_id}", response_model=ServerResponse)
async def update_server(server_id: int, body: ServerUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    update_data = body.model_dump(exclude_unset=True)

    if update_data.get("password"):
        update_data["encrypted_password"] = encrypt(update_data.pop("password"))
    else:
        update_data.pop("password", None)

    if update_data.get("private_key"):
        update_data["encrypted_private_key"] = encrypt(update_data.pop("private_key"))
    else:
        update_data.pop("private_key", None)

    if update_data.get("become_password"):
        update_data["encrypted_become_password"] = encrypt(update_data.pop("become_password"))
    else:
        update_data.pop("become_password", None)

    for key, value in update_data.items():
        if key not in ("password", "private_key", "become_password"):
            setattr(server, key, value)

    await db.commit()
    await db.refresh(server)
    return server


@router.delete("/servers/{server_id}", status_code=204)
async def delete_server(server_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    await db.delete(server)
    await db.commit()


@router.post("/servers/{server_id}/test-connection")
async def test_connection(server_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    success, message = await SSHService.test_connection(server)
    return {"success": success, "message": message}
