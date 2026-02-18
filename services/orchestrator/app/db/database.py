"""
Conexión a base de datos PostgreSQL con SQLAlchemy async
v3 - Engine lazy y resiliente
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import logging
import os

logger = logging.getLogger(__name__)

Base = declarative_base()

# Variables globales - se inicializan después
_engine = None
_session_factory = None
_db_available = False


def get_database_url() -> str:
    """Obtener y convertir URL de base de datos"""
    from ..config import settings
    url = settings.database_url
    logger.info(f"Database URL configured: {url[:20]}...")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


def get_engine():
    """Obtener engine de forma lazy"""
    global _engine
    if _engine is None:
        try:
            url = get_database_url()
            _engine = create_async_engine(
                url,
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True
            )
            logger.info("SQLAlchemy engine created")
        except Exception as e:
            logger.error(f"Failed to create engine: {e}")
            raise
    return _engine


def get_session_factory():
    """Obtener session factory de forma lazy"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _session_factory


async def init_db():
    """Inicializar conexión a BD con reintentos"""
    import asyncio
    global _db_available

    max_retries = 5
    retry_delay = 2

    logger.info("Iniciando conexión a base de datos...")

    for attempt in range(max_retries):
        try:
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Base de datos conectada exitosamente")
            _db_available = True
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Intento {attempt + 1}/{max_retries} - BD no disponible: {e}. Reintentando en {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.warning(f"No se pudo conectar a BD después de {max_retries} intentos: {e}")
                logger.warning("La aplicación continuará sin base de datos")
                _db_available = False


async def close_db():
    """Cerrar conexión a BD"""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
    logger.info("Conexión a BD cerrada")


async def get_db() -> AsyncSession:
    """Dependency para obtener sesión de BD"""
    if not _db_available:
        raise Exception("Database not available")

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def is_db_available() -> bool:
    """Verificar si la BD está disponible"""
    return _db_available
