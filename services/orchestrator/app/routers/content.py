"""
Router para gestión de contenido (avatares, videos)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from typing import List, Optional
import aiohttp

from ..db.database import get_db
from ..models import Avatar, AvatarCreate
from ..config import settings

router = APIRouter()


@router.get("/avatars", response_model=List[Avatar])
async def list_avatars(
    avatar_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Listar todos los avatares"""
    query = "SELECT * FROM content.avatars WHERE is_active = true"
    params = {}

    if avatar_type:
        query += " AND avatar_type = :avatar_type"
        params["avatar_type"] = avatar_type

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return [
        Avatar(
            id=row.id,
            name=row.name,
            description=row.description,
            image_url=row.image_url,
            thumbnail_url=row.thumbnail_url,
            avatar_type=row.avatar_type,
            is_active=row.is_active
        )
        for row in rows
    ]


@router.post("/avatars", response_model=Avatar)
async def create_avatar(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    avatar_type: str = Form("custom"),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Crear nuevo avatar subiendo imagen"""
    # Leer imagen
    image_data = await image.read()

    # TODO: Subir a MinIO
    # Por ahora guardar path local
    image_url = f"/uploads/avatars/{image.filename}"

    # Guardar en BD
    result = await db.execute(
        text("""
            INSERT INTO content.avatars (name, description, avatar_type, image_url)
            VALUES (:name, :description, :avatar_type, :image_url)
            RETURNING *
        """),
        {
            "name": name,
            "description": description,
            "avatar_type": avatar_type,
            "image_url": image_url
        }
    )
    await db.commit()
    row = result.fetchone()

    return Avatar(
        id=row.id,
        name=row.name,
        description=row.description,
        image_url=row.image_url,
        thumbnail_url=row.thumbnail_url,
        avatar_type=row.avatar_type,
        is_active=row.is_active
    )


@router.get("/avatars/{avatar_id}", response_model=Avatar)
async def get_avatar(
    avatar_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Obtener un avatar por ID"""
    result = await db.execute(
        text("SELECT * FROM content.avatars WHERE id = :avatar_id"),
        {"avatar_id": str(avatar_id)}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Avatar no encontrado")

    return Avatar(
        id=row.id,
        name=row.name,
        description=row.description,
        image_url=row.image_url,
        thumbnail_url=row.thumbnail_url,
        avatar_type=row.avatar_type,
        is_active=row.is_active
    )


@router.delete("/avatars/{avatar_id}")
async def delete_avatar(
    avatar_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Desactivar un avatar"""
    result = await db.execute(
        text("""
            UPDATE content.avatars SET is_active = false
            WHERE id = :avatar_id
            RETURNING id
        """),
        {"avatar_id": str(avatar_id)}
    )
    await db.commit()
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Avatar no encontrado")

    return {"status": "deleted", "avatar_id": str(avatar_id)}


@router.post("/avatars/{avatar_id}/generate-animation")
async def generate_animation(
    avatar_id: UUID,
    driving_source: str = "natural",
    duration_seconds: float = 5.0,
    db: AsyncSession = Depends(get_db)
):
    """Generar animación para un avatar usando FasterLivePortrait"""
    # Obtener avatar
    result = await db.execute(
        text("SELECT * FROM content.avatars WHERE id = :avatar_id"),
        {"avatar_id": str(avatar_id)}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Avatar no encontrado")

    # TODO: Llamar a FasterLivePortrait API
    # Por ahora retornar job_id simulado

    return {
        "job_id": f"anim_{avatar_id}",
        "avatar_id": str(avatar_id),
        "status": "queued",
        "driving_source": driving_source,
        "duration_seconds": duration_seconds
    }
