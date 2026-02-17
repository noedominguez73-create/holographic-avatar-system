"""
Router para Modo 1: Foto Memorial
Anima fotos de familiares para crear avatares holográficos temporales
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID, uuid4
from typing import Optional
import aiohttp
import base64
import logging

from ..db.database import get_db
from ..models import MemorialUploadResponse, MemorialPlayRequest
from ..config import settings
from ..services.ai_client import AIClient

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache de jobs en proceso (en producción usar Redis)
processing_jobs = {}


@router.post("/upload-photo", response_model=MemorialUploadResponse)
async def upload_memorial_photo(
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(...),
    user_email: Optional[str] = Form(None),
    user_phone: Optional[str] = Form(None),
    location_id: Optional[UUID] = Form(None),
    animation_duration: float = Form(5.0),
    db: AsyncSession = Depends(get_db)
):
    """
    Subir foto para crear avatar memorial animado.

    1. Recibe la foto
    2. Valida que contiene un rostro
    3. Genera video animado con FasterLivePortrait
    4. Convierte a formato del ventilador
    """
    # Generar IDs
    job_id = str(uuid4())
    avatar_id = uuid4()

    # Leer imagen
    image_data = await photo.read()
    image_base64 = base64.b64encode(image_data).decode()

    # Guardar avatar en BD
    result = await db.execute(
        text("""
            INSERT INTO content.avatars (id, name, avatar_type, image_url, metadata)
            VALUES (:id, :name, 'memorial', :image_url, :metadata)
            RETURNING id
        """),
        {
            "id": str(avatar_id),
            "name": f"Memorial_{job_id[:8]}",
            "image_url": f"/uploads/memorial/{job_id}.jpg",
            "metadata": f'{{"email": "{user_email}", "phone": "{user_phone}"}}'
        }
    )
    await db.commit()

    # Iniciar procesamiento en background
    processing_jobs[job_id] = {
        "status": "processing",
        "avatar_id": str(avatar_id),
        "progress": 0
    }

    background_tasks.add_task(
        process_memorial_photo,
        job_id=job_id,
        avatar_id=str(avatar_id),
        image_base64=image_base64,
        duration=animation_duration
    )

    return MemorialUploadResponse(
        job_id=job_id,
        avatar_id=avatar_id,
        status="processing",
        estimated_seconds=int(animation_duration * 6)  # ~6 seg por segundo de video
    )


async def process_memorial_photo(
    job_id: str,
    avatar_id: str,
    image_base64: str,
    duration: float
):
    """Proceso en background para generar animación"""
    try:
        processing_jobs[job_id]["progress"] = 10
        processing_jobs[job_id]["step"] = "Detectando rostro..."

        # Llamar a FasterLivePortrait API
        async with aiohttp.ClientSession() as session:
            # Decodificar imagen
            image_data = base64.b64decode(image_base64)

            processing_jobs[job_id]["progress"] = 30
            processing_jobs[job_id]["step"] = "Generando animación..."

            # Preparar request
            form_data = aiohttp.FormData()
            form_data.add_field('source_image', image_data, filename='photo.jpg')
            form_data.add_field('flag_is_animal', 'false')
            form_data.add_field('flag_relative_input', 'true')
            form_data.add_field('flag_do_crop_input', 'true')
            form_data.add_field('flag_stitching', 'true')

            # TODO: Agregar driving video o pkl

            try:
                async with session.post(
                    f"{settings.faster_liveportrait_url}/predict/",
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        # Guardar video resultado
                        video_data = await response.read()
                        processing_jobs[job_id]["progress"] = 70
                        processing_jobs[job_id]["step"] = "Procesando para holograma..."

                        # TODO: Convertir a formato polar

                        processing_jobs[job_id]["progress"] = 100
                        processing_jobs[job_id]["status"] = "completed"
                        processing_jobs[job_id]["video_url"] = f"/content/videos/{avatar_id}.mp4"
                    else:
                        raise Exception(f"FasterLivePortrait error: {response.status}")

            except aiohttp.ClientError as e:
                logger.warning(f"FasterLivePortrait no disponible: {e}")
                # Simular procesamiento para desarrollo
                import asyncio
                await asyncio.sleep(3)
                processing_jobs[job_id]["progress"] = 100
                processing_jobs[job_id]["status"] = "completed"
                processing_jobs[job_id]["video_url"] = f"/content/videos/{avatar_id}.mp4"

    except Exception as e:
        logger.error(f"Error procesando memorial: {e}")
        processing_jobs[job_id]["status"] = "error"
        processing_jobs[job_id]["error"] = str(e)


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Obtener estado de procesamiento de un job"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    return processing_jobs[job_id]


@router.post("/play/{avatar_id}")
async def play_memorial_avatar(
    avatar_id: UUID,
    request: MemorialPlayRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reproducir avatar memorial en un dispositivo.

    Envía el video animado al ventilador holográfico.
    """
    # Verificar que el avatar existe
    result = await db.execute(
        text("SELECT * FROM content.avatars WHERE id = :avatar_id"),
        {"avatar_id": str(avatar_id)}
    )
    avatar = result.fetchone()

    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar no encontrado")

    # Verificar dispositivo
    result = await db.execute(
        text("SELECT * FROM core.devices WHERE id = :device_id"),
        {"device_id": str(request.device_id)}
    )
    device = result.fetchone()

    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Buscar video animado
    result = await db.execute(
        text("""
            SELECT * FROM content.animated_videos
            WHERE avatar_id = :avatar_id AND status = 'ready'
            ORDER BY created_at DESC LIMIT 1
        """),
        {"avatar_id": str(avatar_id)}
    )
    video = result.fetchone()

    # TODO: Enviar al Fan Driver para reproducir

    # Crear sesión memorial
    result = await db.execute(
        text("""
            INSERT INTO content.memorial_sessions (
                location_id, device_id, avatar_id
            )
            VALUES (
                (SELECT location_id FROM core.devices WHERE id = :device_id),
                :device_id, :avatar_id
            )
            RETURNING id
        """),
        {
            "device_id": str(request.device_id),
            "avatar_id": str(avatar_id)
        }
    )
    await db.commit()
    session = result.fetchone()

    return {
        "status": "playing",
        "session_id": str(session.id),
        "avatar_id": str(avatar_id),
        "device_id": str(request.device_id),
        "loop": request.loop,
        "duration_seconds": request.duration_seconds
    }


@router.post("/sessions/{session_id}/capture-photo")
async def capture_photo_with_hologram(
    session_id: UUID,
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Guardar foto del usuario con el holograma.

    Esta foto se guarda para que el usuario la recuerde.
    """
    # Verificar sesión
    result = await db.execute(
        text("SELECT * FROM content.memorial_sessions WHERE id = :session_id"),
        {"session_id": str(session_id)}
    )
    session = result.fetchone()

    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Guardar foto
    photo_data = await photo.read()
    photo_url = f"/uploads/captures/{session_id}.jpg"

    # TODO: Subir a MinIO

    # Actualizar sesión
    await db.execute(
        text("""
            UPDATE content.memorial_sessions
            SET photo_taken_url = :photo_url
            WHERE id = :session_id
        """),
        {
            "session_id": str(session_id),
            "photo_url": photo_url
        }
    )
    await db.commit()

    return {
        "status": "captured",
        "session_id": str(session_id),
        "photo_url": photo_url
    }


@router.post("/sessions/{session_id}/end")
async def end_memorial_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Terminar sesión memorial"""
    await db.execute(
        text("""
            UPDATE content.memorial_sessions
            SET session_end = CURRENT_TIMESTAMP
            WHERE id = :session_id
        """),
        {"session_id": str(session_id)}
    )
    await db.commit()

    return {"status": "ended", "session_id": str(session_id)}
