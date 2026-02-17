"""
Router para gestión de sesiones
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from typing import List

from ..db.database import get_db
from ..models import Session, SessionCreate, SessionStatus

router = APIRouter()


@router.post("/", response_model=Session)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Iniciar nueva sesión en un dispositivo"""
    # Verificar que el dispositivo existe y está disponible
    result = await db.execute(
        text("SELECT id, status FROM core.devices WHERE id = :device_id"),
        {"device_id": str(session_data.device_id)}
    )
    device = result.fetchone()

    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    if device.status == "busy":
        raise HTTPException(status_code=409, detail="Dispositivo ocupado")

    # Crear sesión
    result = await db.execute(
        text("""
            INSERT INTO conversations.sessions (device_id, mode, metadata)
            VALUES (:device_id, :mode, :metadata)
            RETURNING id, device_id, mode, started_at
        """),
        {
            "device_id": str(session_data.device_id),
            "mode": session_data.mode.value,
            "metadata": str(session_data.config)
        }
    )
    await db.commit()

    row = result.fetchone()

    # Marcar dispositivo como ocupado
    await db.execute(
        text("UPDATE core.devices SET status = 'busy' WHERE id = :device_id"),
        {"device_id": str(session_data.device_id)}
    )
    await db.commit()

    return Session(
        id=row.id,
        device_id=row.device_id,
        mode=row.mode,
        avatar_id=session_data.avatar_id,
        status=SessionStatus.ACTIVE,
        started_at=row.started_at,
        ended_at=None,
        metadata=session_data.config or {}
    )


@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Obtener estado de una sesión"""
    result = await db.execute(
        text("""
            SELECT id, device_id, mode, started_at, ended_at, metadata
            FROM conversations.sessions
            WHERE id = :session_id
        """),
        {"session_id": str(session_id)}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    status = SessionStatus.ENDED if row.ended_at else SessionStatus.ACTIVE

    return Session(
        id=row.id,
        device_id=row.device_id,
        mode=row.mode,
        avatar_id=None,
        status=status,
        started_at=row.started_at,
        ended_at=row.ended_at,
        metadata=row.metadata or {}
    )


@router.delete("/{session_id}")
async def end_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Terminar una sesión"""
    # Obtener sesión
    result = await db.execute(
        text("SELECT device_id FROM conversations.sessions WHERE id = :session_id"),
        {"session_id": str(session_id)}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Marcar sesión como terminada
    await db.execute(
        text("""
            UPDATE conversations.sessions
            SET ended_at = CURRENT_TIMESTAMP
            WHERE id = :session_id
        """),
        {"session_id": str(session_id)}
    )

    # Liberar dispositivo
    await db.execute(
        text("UPDATE core.devices SET status = 'online' WHERE id = :device_id"),
        {"device_id": str(row.device_id)}
    )
    await db.commit()

    return {"status": "ended", "session_id": str(session_id)}


@router.get("/", response_model=List[Session])
async def list_active_sessions(
    location_id: UUID = None,
    db: AsyncSession = Depends(get_db)
):
    """Listar sesiones activas"""
    query = """
        SELECT s.id, s.device_id, s.mode, s.started_at, s.ended_at, s.metadata
        FROM conversations.sessions s
        JOIN core.devices d ON s.device_id = d.id
        WHERE s.ended_at IS NULL
    """
    params = {}

    if location_id:
        query += " AND d.location_id = :location_id"
        params["location_id"] = str(location_id)

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return [
        Session(
            id=row.id,
            device_id=row.device_id,
            mode=row.mode,
            avatar_id=None,
            status=SessionStatus.ACTIVE,
            started_at=row.started_at,
            ended_at=None,
            metadata=row.metadata or {}
        )
        for row in rows
    ]
