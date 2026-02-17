"""
Holographic Avatar System - Orchestrator Service
Servicio principal que coordina todos los modos de operación
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import settings
from .routers import sessions, modes, content, devices, locations
from .routers import memorial, receptionist, menu, catalog, videocall
from .db.database import init_db, close_db

# Configurar logging
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
        logger.info("Base de datos conectada")
    except Exception as e:
        logger.warning(f"Base de datos no disponible: {e}")
        logger.info("Continuando en modo sin BD (solo para pruebas)")
    yield
    logger.info("Cerrando Holographic Avatar System...")
    try:
        await close_db()
    except:
        pass


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

# Routers principales
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])
app.include_router(modes.router, prefix="/api/v1/modes", tags=["Modes"])
app.include_router(content.router, prefix="/api/v1/content", tags=["Content"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["Devices"])
app.include_router(locations.router, prefix="/api/v1/locations", tags=["Locations"])

# Routers de modos específicos
app.include_router(memorial.router, prefix="/api/v1/memorial", tags=["Modo Memorial"])
app.include_router(receptionist.router, prefix="/api/v1/receptionist", tags=["Modo Recepcionista"])
app.include_router(menu.router, prefix="/api/v1/menu", tags=["Modo Menú"])
app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["Modo Catálogo"])
app.include_router(videocall.router, prefix="/api/v1/videocall", tags=["Modo Videollamada"])


@app.get("/")
async def root():
    return {
        "service": "Holographic Avatar System",
        "version": "1.0.0",
        "status": "running",
        "modes": ["memorial", "receptionist", "menu", "catalog", "videocall"]
    }


@app.get("/health")
async def health_check():
    import os
    return {
        "status": "healthy",
        "service": "holographic-avatar-orchestrator",
        "version": "1.0.0",
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "local")
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
