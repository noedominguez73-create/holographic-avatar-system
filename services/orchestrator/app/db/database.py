"""
Conexión a base de datos PostgreSQL con SQLAlchemy async
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import logging
import os

logger = logging.getLogger(__name__)

Base = declarative_base()

# Variables globales - se inicializan lazy
engine = None
AsyncSessionLocal = None


def _get_database_url() -> str:
    """Obtiene URL de BD de forma segura"""
    try:
        from ..config import settings
        url = settings.database_url
    except ImportError:
        url = os.getenv("DATABASE_URL", "postgresql://holographic:holographic_secret@localhost:5432/holographic_avatar")

    # Convertir a async URL
    if url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


def _create_engine():
    """Crea el engine de forma lazy"""
    global engine, AsyncSessionLocal
    if engine is not None:
        return engine

    try:
        DATABASE_URL = _get_database_url()
        if not DATABASE_URL:
            logger.warning("DATABASE_URL no definida")
            return None

        engine = create_async_engine(
            DATABASE_URL,
            echo=os.getenv("DEBUG", "false").lower() == "true",
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={
                "timeout": 5,
                "statement_cache_size": 0,
            }
        )
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("Engine de BD creado")
    except Exception as e:
        logger.warning(f"No se pudo crear engine de BD: {e}")
        engine = None
        AsyncSessionLocal = None

    return engine


async def init_db():
    """Inicializar conexión a BD - No bloqueante para Health Check"""
    eng = _create_engine()
    if eng is None:
        logger.warning("BD no configurada, continuando sin persistencia")
        return

    try:
        # Intentar conectar con timeout corto (definido en create_async_engine)
        async with eng.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Conexión a base de datos establecida exitosamente")
    except Exception as e:
        # CRITICO: Capturar excepción para permitir que la app arranque
        # y pase el Health Check de Railway (30s)
        logger.error(f"⚠️ BD no disponible al inicio: {e}")
        logger.warning("➡️ La aplicación continuará iniciando en modo degradado")
        
        # No hacemos raise aqui para que main.py continue


async def close_db():
    """Cerrar conexión a BD"""
    global engine
    if engine is not None:
        await engine.dispose()
        logger.info("Conexión a base de datos cerrada")


async def get_db() -> AsyncSession:
    """Dependency para obtener sesión de BD"""
    if AsyncSessionLocal is None:
        # Intentar recrear si falló al inicio
        _create_engine()
        
    if AsyncSessionLocal is None:
         # Si sigue fallando, es un error 500 para el endpoint que necesite BD
        raise Exception("Base de datos no disponible temporalmente")

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
