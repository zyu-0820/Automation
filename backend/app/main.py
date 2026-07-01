import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from app.config import settings
from app.database import Base, engine
from app.routers import configs, jars, operations, servers, services
from app.utils.encryption import ensure_encryption_key
from app.utils.errors import AppError
from app.utils.migrate import auto_migrate


@asynccontextmanager
async def lifespan(app: FastAPI):
    await auto_migrate(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    ensure_encryption_key()
    yield


app = FastAPI(title="Java Service Manager", lifespan=lifespan)

app.include_router(servers.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(configs.router, prefix="/api")
app.include_router(jars.router, prefix="/api")
app.include_router(operations.router, prefix="/api")

static_dir = os.environ.get("STATIC_DIR", "")
if static_dir and os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": str(exc)}},
    )
