"""
Holographic Avatar System - Orchestrator Service
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

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

# Determinar ruta del kiosk-app
# En desarrollo: ../../../kiosk-app relativo a este archivo
# En producción (Railway): /app/kiosk-app
KIOSK_APP_PATH = None

# Intentar encontrar kiosk-app
possible_paths = [
    Path("/app/kiosk-app"),  # Railway
    Path(__file__).parent.parent.parent.parent / "kiosk-app",  # Local dev
    Path.cwd() / "kiosk-app",  # Current directory
]

for path in possible_paths:
    if path.exists() and (path / "index.html").exists():
        KIOSK_APP_PATH = path
        logger.info(f"Kiosk app encontrado en: {KIOSK_APP_PATH}")
        break

if KIOSK_APP_PATH:
    # Montar archivos estáticos (CSS, JS, imágenes)
    app.mount("/css", StaticFiles(directory=KIOSK_APP_PATH / "css"), name="css")
    app.mount("/js", StaticFiles(directory=KIOSK_APP_PATH / "js"), name="js")
    if (KIOSK_APP_PATH / "images").exists():
        app.mount("/images", StaticFiles(directory=KIOSK_APP_PATH / "images"), name="images")
    if (KIOSK_APP_PATH / "assets").exists():
        app.mount("/assets", StaticFiles(directory=KIOSK_APP_PATH / "assets"), name="assets")


@app.get("/")
async def root():
    """Serve kiosk app or API info"""
    if KIOSK_APP_PATH and (KIOSK_APP_PATH / "index.html").exists():
        return FileResponse(KIOSK_APP_PATH / "index.html")
    return {
        "service": "Holographic Avatar System",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/admin.html")
async def admin_page():
    """Serve admin dashboard"""
    if KIOSK_APP_PATH and (KIOSK_APP_PATH / "admin.html").exists():
        return FileResponse(KIOSK_APP_PATH / "admin.html")
    return {"error": "Admin page not found"}


@app.get("/index.html")
async def index_page():
    """Serve main kiosk app"""
    if KIOSK_APP_PATH and (KIOSK_APP_PATH / "index.html").exists():
        return FileResponse(KIOSK_APP_PATH / "index.html")
    return {"error": "Index page not found"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "orchestrator",
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "local")
    }
