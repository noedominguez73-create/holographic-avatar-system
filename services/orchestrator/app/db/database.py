"""
Conexión a base de datos PostgreSQL con SQLAlchemy async
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import logging

from ..config import settings

logger = logging.getLogger(__name__)

# Convertir URL a async
DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def init_db():
    """Inicializar conexión a BD"""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Conexión a base de datos establecida")
    except Exception as e:
        logger.error(f"Error conectando a BD: {e}")
        raise


async def close_db():
    """Cerrar conexión a BD"""
    await engine.dispose()
    logger.info("Conexión a base de datos cerrada")


async def get_db() -> AsyncSession:
    """Dependency para obtener sesión de BD"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
