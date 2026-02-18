"""
Holographic Avatar System - Orchestrator Service
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from .config import settings
from .routers import sessions, modes, content, devices, locations
from .routers import memorial, receptionist, menu, catalog, videocall
from .db.database import init_db, close_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle del servidor"""
    logger.info("Iniciando Holographic Avatar System...")
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Error en init_db (no fatal): {e}")
    logger.info("Servidor listo para recibir requests")
    yield
    logger.info("Cerrando Holographic Avatar System...")
    try:
        await close_db()
    except Exception as e:
        logger.error(f"Error en close_db: {e}")


app = FastAPI(
    title="Holographic Avatar System",
    description="Sistema modular de avatar holográfico para ventiladores LED 3D",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])
app.include_router(modes.router, prefix="/api/v1/modes", tags=["Modes"])
app.include_router(content.router, prefix="/api/v1/content", tags=["Content"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["Devices"])
app.include_router(locations.router, prefix="/api/v1/locations", tags=["Locations"])
app.include_router(memorial.router, prefix="/api/v1/memorial", tags=["Memorial"])
app.include_router(receptionist.router, prefix="/api/v1/receptionist", tags=["Recepcionista"])
app.include_router(menu.router, prefix="/api/v1/menu", tags=["Menú"])
app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["Catálogo"])
app.include_router(videocall.router, prefix="/api/v1/videocall", tags=["Videollamada"])


@app.get("/")
async def root():
    return {
        "service": "Holographic Avatar System",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "orchestrator",
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "local")
    }
