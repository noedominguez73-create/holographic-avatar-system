"""
Router para gestión de dispositivos (ventiladores holográficos)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from typing import List

from ..db.database import get_db
from ..models import Device, DeviceCreate, DeviceStatus

router = APIRouter()


@router.get("/", response_model=List[Device])
async def list_devices(
    location_id: UUID = None,
    status: DeviceStatus = None,
    db: AsyncSession = Depends(get_db)
):
    """Listar todos los dispositivos"""
    query = "SELECT * FROM core.devices WHERE 1=1"
    params = {}

    if location_id:
        query += " AND location_id = :location_id"
        params["location_id"] = str(location_id)

    if status:
        query += " AND status = :status"
        params["status"] = status.value

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return [
        Device(
            id=row.id,
            location_id=row.location_id,
            name=row.name,
            ip_address=str(row.ip_address),
            device_type=row.device_type,
            protocol_type=row.protocol_type,
            status=DeviceStatus(row.status),
            last_heartbeat=row.last_heartbeat
        )
        for row in rows
    ]


@router.post("/", response_model=Device)
async def create_device(
    device: DeviceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Registrar nuevo dispositivo"""
    result = await db.execute(
        text("""
            INSERT INTO core.devices (
                location_id, name, ip_address, device_type,
                protocol_type, tcp_port, http_port, status
            )
            VALUES (
                :location_id, :name, :ip_address, :device_type,
                :protocol_type, :tcp_port, :http_port, 'offline'
            )
            RETURNING *
        """),
        {
            "location_id": str(device.location_id),
            "name": device.name,
            "ip_address": device.ip_address,
            "device_type": device.device_type,
            "protocol_type": device.protocol_type,
            "tcp_port": device.tcp_port,
            "http_port": device.http_port
        }
    )
    await db.commit()
    row = result.fetchone()

    return Device(
        id=row.id,
        location_id=row.location_id,
        name=row.name,
        ip_address=str(row.ip_address),
        device_type=row.device_type,
        protocol_type=row.protocol_type,
        status=DeviceStatus(row.status),
        last_heartbeat=row.last_heartbeat
    )


@router.get("/{device_id}", response_model=Device)
async def get_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Obtener información de un dispositivo"""
    result = await db.execute(
        text("SELECT * FROM core.devices WHERE id = :device_id"),
        {"device_id": str(device_id)}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    return Device(
        id=row.id,
        location_id=row.location_id,
        name=row.name,
        ip_address=str(row.ip_address),
        device_type=row.device_type,
        protocol_type=row.protocol_type,
        status=DeviceStatus(row.status),
        last_heartbeat=row.last_heartbeat
    )


@router.put("/{device_id}", response_model=Device)
async def update_device(
    device_id: UUID,
    device: DeviceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Actualizar configuración de dispositivo"""
    result = await db.execute(
        text("""
            UPDATE core.devices SET
                location_id = :location_id,
                name = :name,
                ip_address = :ip_address,
                device_type = :device_type,
                protocol_type = :protocol_type,
                tcp_port = :tcp_port,
                http_port = :http_port
            WHERE id = :device_id
            RETURNING *
        """),
        {
            "device_id": str(device_id),
            "location_id": str(device.location_id),
            "name": device.name,
            "ip_address": device.ip_address,
            "device_type": device.device_type,
            "protocol_type": device.protocol_type,
            "tcp_port": device.tcp_port,
            "http_port": device.http_port
        }
    )
    await db.commit()
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    return Device(
        id=row.id,
        location_id=row.location_id,
        name=row.name,
        ip_address=str(row.ip_address),
        device_type=row.device_type,
        protocol_type=row.protocol_type,
        status=DeviceStatus(row.status),
        last_heartbeat=row.last_heartbeat
    )


@router.delete("/{device_id}")
async def delete_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Eliminar dispositivo"""
    result = await db.execute(
        text("DELETE FROM core.devices WHERE id = :device_id RETURNING id"),
        {"device_id": str(device_id)}
    )
    await db.commit()
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    return {"status": "deleted", "device_id": str(device_id)}


@router.post("/{device_id}/ping")
async def ping_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Hacer ping a un dispositivo para verificar conectividad"""
    # Obtener IP del dispositivo
    result = await db.execute(
        text("SELECT ip_address FROM core.devices WHERE id = :device_id"),
        {"device_id": str(device_id)}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # TODO: Implementar ping real al dispositivo
    # Por ahora simular respuesta

    # Actualizar heartbeat
    await db.execute(
        text("""
            UPDATE core.devices
            SET status = 'online', last_heartbeat = CURRENT_TIMESTAMP
            WHERE id = :device_id
        """),
        {"device_id": str(device_id)}
    )
    await db.commit()

    return {"status": "online", "ip_address": str(row.ip_address)}
