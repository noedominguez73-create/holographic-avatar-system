"""
Router para gestión de ubicaciones
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from typing import List

from ..db.database import get_db
from ..models import Location, LocationCreate

router = APIRouter()


@router.get("/", response_model=List[Location])
async def list_locations(
    db: AsyncSession = Depends(get_db)
):
    """Listar todas las ubicaciones"""
    result = await db.execute(
        text("""
            SELECT l.*, COUNT(d.id) as devices_count
            FROM core.locations l
            LEFT JOIN core.devices d ON l.id = d.location_id
            WHERE l.is_active = true
            GROUP BY l.id
        """)
    )
    rows = result.fetchall()

    return [
        Location(
            id=row.id,
            name=row.name,
            address=row.address,
            city=row.city,
            is_active=row.is_active,
            devices_count=row.devices_count or 0
        )
        for row in rows
    ]


@router.post("/", response_model=Location)
async def create_location(
    location: LocationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crear nueva ubicación"""
    result = await db.execute(
        text("""
            INSERT INTO core.locations (name, address, city, timezone)
            VALUES (:name, :address, :city, :timezone)
            RETURNING *
        """),
        {
            "name": location.name,
            "address": location.address,
            "city": location.city,
            "timezone": location.timezone
        }
    )
    await db.commit()
    row = result.fetchone()

    return Location(
        id=row.id,
        name=row.name,
        address=row.address,
        city=row.city,
        is_active=row.is_active,
        devices_count=0
    )


@router.get("/{location_id}", response_model=Location)
async def get_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Obtener una ubicación por ID"""
    result = await db.execute(
        text("""
            SELECT l.*, COUNT(d.id) as devices_count
            FROM core.locations l
            LEFT JOIN core.devices d ON l.id = d.location_id
            WHERE l.id = :location_id
            GROUP BY l.id
        """),
        {"location_id": str(location_id)}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")

    return Location(
        id=row.id,
        name=row.name,
        address=row.address,
        city=row.city,
        is_active=row.is_active,
        devices_count=row.devices_count or 0
    )


@router.put("/{location_id}", response_model=Location)
async def update_location(
    location_id: UUID,
    location: LocationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Actualizar ubicación"""
    result = await db.execute(
        text("""
            UPDATE core.locations SET
                name = :name,
                address = :address,
                city = :city,
                timezone = :timezone
            WHERE id = :location_id
            RETURNING *
        """),
        {
            "location_id": str(location_id),
            "name": location.name,
            "address": location.address,
            "city": location.city,
            "timezone": location.timezone
        }
    )
    await db.commit()
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")

    return Location(
        id=row.id,
        name=row.name,
        address=row.address,
        city=row.city,
        is_active=row.is_active,
        devices_count=0
    )


@router.delete("/{location_id}")
async def delete_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Desactivar ubicación"""
    result = await db.execute(
        text("""
            UPDATE core.locations SET is_active = false
            WHERE id = :location_id
            RETURNING id
        """),
        {"location_id": str(location_id)}
    )
    await db.commit()
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")

    return {"status": "deleted", "location_id": str(location_id)}


@router.post("/{location_id}/sync")
async def sync_content_to_location(
    location_id: UUID,
    content_ids: List[UUID],
    db: AsyncSession = Depends(get_db)
):
    """Sincronizar contenido a una ubicación"""
    # Verificar que la ubicación existe
    result = await db.execute(
        text("SELECT id FROM core.locations WHERE id = :location_id"),
        {"location_id": str(location_id)}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")

    # TODO: Implementar sincronización de contenido

    return {
        "status": "synced",
        "location_id": str(location_id),
        "content_ids": [str(cid) for cid in content_ids]
    }
