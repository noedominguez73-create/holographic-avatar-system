"""
Conexión a base de datos PostgreSQL con SQLAlchemy async
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import logging

from ..config import settings

logger = logging.getLogger(__name__)

# Convertir URL a formato async
def get_database_url() -> str:
    url = settings.database_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url

DATABASE_URL = get_database_url()

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def init_db():
    """Inicializar conexión a BD"""
    import asyncio
    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Base de datos conectada")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Intento {attempt + 1}/{max_retries} - BD no disponible: {e}. Reintentando en {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.warning(f"No se pudo conectar a BD después de {max_retries} intentos. La app continuará sin BD.")
                # No hacer raise - la app sigue funcionando para el healthcheck


async def close_db():
    """Cerrar conexión a BD"""
    await engine.dispose()
    logger.info("Conexión a BD cerrada")


async def get_db() -> AsyncSession:
    """Dependency para obtener sesión de BD"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
