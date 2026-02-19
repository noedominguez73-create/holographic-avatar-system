"""
Router para Modo 5: Videollamada en Vivo
Transmite persona real al ventilador holográfico via WebRTC
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID, uuid4
from typing import Optional, Dict, Any
import logging
import json
import asyncio
import aiohttp

from ..db.database import get_db
from ..models import VideocallStartRequest, VideocallStartResponse, ICECandidate
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Sesiones activas de videollamada
videocall_sessions: Dict[str, Dict[str, Any]] = {}


@router.post("/start", response_model=VideocallStartResponse)
async def start_videocall(
    request: VideocallStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Iniciar sesión de videollamada WebRTC.

    1. Recibe oferta SDP del cliente
    2. Configura el pipeline de procesamiento
    3. Retorna respuesta SDP
    """
    # Verificar dispositivo
    result = await db.execute(
        text("SELECT * FROM core.devices WHERE id = :device_id"),
        {"device_id": str(request.device_id)}
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
            VALUES (:device_id, 'videocall', :metadata)
            RETURNING id, started_at
        """),
        {
            "device_id": str(request.device_id),
            "metadata": json.dumps({
                "caller_id": request.caller_id,
                "type": "webrtc"
            })
        }
    )
    await db.commit()
    session_row = result.fetchone()
    session_id = session_row.id

    # Marcar dispositivo como ocupado
    await db.execute(
        text("UPDATE core.devices SET status = 'busy' WHERE id = :device_id"),
        {"device_id": str(request.device_id)}
    )
    await db.commit()

    # Procesar oferta SDP
    # TODO: Usar aiortc para manejar WebRTC
    # Por ahora simular respuesta

    sdp_answer = _create_sdp_answer(request.webrtc_offer)
    ice_candidates = _generate_ice_candidates()

    # Guardar sesión en cache
    videocall_sessions[str(session_id)] = {
        "device_id": str(request.device_id),
        "fan_ip": device.ip_address,
        "caller_id": request.caller_id,
        "status": "connecting",
        "offer": request.webrtc_offer,
        "answer": sdp_answer,
        "ice_candidates": ice_candidates,
        "frame_buffer": asyncio.Queue(maxsize=30)
    }

    return VideocallStartResponse(
        session_id=session_id,
        webrtc_answer=sdp_answer,
        ice_candidates=ice_candidates
    )


@router.post("/{session_id}/ice")
async def add_ice_candidate(
    session_id: UUID,
    candidate: ICECandidate
):
    """Agregar ICE candidate para conexión WebRTC"""
    session_id_str = str(session_id)

    if session_id_str not in videocall_sessions:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    session = videocall_sessions[session_id_str]
    session.setdefault("remote_ice_candidates", []).append({
        "candidate": candidate.candidate,
        "sdpMid": candidate.sdpMid,
        "sdpMLineIndex": candidate.sdpMLineIndex
    })

    # TODO: Pasar candidato a aiortc

    return {"status": "added", "session_id": session_id_str}


@router.post("/{session_id}/end")
async def end_videocall(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Terminar videollamada"""
    session_id_str = str(session_id)

    if session_id_str in videocall_sessions:
        session = videocall_sessions[session_id_str]

        # Liberar dispositivo
        await db.execute(
            text("UPDATE core.devices SET status = 'online' WHERE id = :device_id"),
            {"device_id": session["device_id"]}
        )

        # TODO: Cerrar conexión WebRTC

        del videocall_sessions[session_id_str]

    # Marcar sesión como terminada
    await db.execute(
        text("""
            UPDATE conversations.sessions
            SET ended_at = CURRENT_TIMESTAMP
            WHERE id = :session_id
        """),
        {"session_id": session_id_str}
    )
    await db.commit()

    return {"status": "ended", "session_id": session_id_str}


@router.get("/{session_id}/status")
async def get_videocall_status(session_id: UUID):
    """Obtener estado de la videollamada"""
    session_id_str = str(session_id)

    if session_id_str not in videocall_sessions:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    session = videocall_sessions[session_id_str]

    return {
        "session_id": session_id_str,
        "status": session.get("status", "unknown"),
        "caller_id": session.get("caller_id"),
        "device_id": session.get("device_id"),
        "frames_processed": session.get("frames_processed", 0),
        "current_fps": session.get("current_fps", 0)
    }


@router.websocket("/stream/{session_id}")
async def websocket_stream(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket para streaming de frames en tiempo real.

    Recibe frames del cliente y los procesa para enviar al ventilador.
    """
    await websocket.accept()

    if session_id not in videocall_sessions:
        await websocket.close(code=4004, reason="Sesión no encontrada")
        return

    session = videocall_sessions[session_id]
    session["status"] = "streaming"
    session["frames_processed"] = 0

    try:
        while True:
            # Recibir frame
            data = await websocket.receive_bytes()

            # Procesar frame
            processed_frame = await _process_frame(data, session)

            # Enviar al ventilador
            await _send_to_fan(processed_frame, session)

            session["frames_processed"] += 1

            # Enviar confirmación
            await websocket.send_json({
                "status": "ok",
                "frame": session["frames_processed"]
            })

    except WebSocketDisconnect:
        logger.info(f"Videocall {session_id} desconectada")
        session["status"] = "disconnected"
    except Exception as e:
        logger.error(f"Error en streaming: {e}")
        session["status"] = "error"


async def _process_frame(frame_data: bytes, session: dict) -> bytes:
    """
    Procesar frame para el ventilador.

    1. Enviar a Frame Processor service
    2. Recibe imagen procesada (fondo negro, circular, 256x256)
    """
    import cv2
    import numpy as np

    frame_processor_url = getattr(settings, 'FRAME_PROCESSOR_URL', 'http://frame-processor:8010')

    try:
        async with aiohttp.ClientSession() as http:
            form = aiohttp.FormData()
            form.add_field('frame', frame_data, filename='frame.jpg', content_type='image/jpeg')

            async with http.post(
                f'{frame_processor_url}/process',
                data=form,
                params={
                    'target_size': 256,
                    'circular_crop': 'true',
                    'remove_background': 'true',
                    'brightness_boost': 1.3,
                    'contrast_boost': 1.2
                },
                timeout=aiohttp.ClientTimeout(total=0.5)
            ) as resp:
                if resp.status == 200:
                    return await resp.read()

    except Exception as e:
        logger.warning(f"Frame processor no disponible, usando fallback: {e}")

    # Fallback: procesamiento básico local
    nparr = np.frombuffer(frame_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return b''

    # Resize a 256x256
    frame = cv2.resize(frame, (256, 256))

    # Aplicar máscara circular básica
    mask = np.zeros((256, 256), dtype=np.uint8)
    cv2.circle(mask, (128, 128), 128, 255, -1)
    frame = cv2.bitwise_and(frame, frame, mask=mask)

    # Codificar como PNG
    _, encoded = cv2.imencode('.png', frame)
    return encoded.tobytes()


async def _send_to_fan(frame_data: bytes, session: dict):
    """
    Enviar frame procesado al ventilador.

    1. Convertir imagen a formato polar (polar-encoder)
    2. Enviar datos polares al ventilador (fan-driver)
    """
    polar_encoder_url = getattr(settings, 'POLAR_ENCODER_URL', 'http://polar-encoder:8011')
    fan_driver_url = getattr(settings, 'FAN_DRIVER_URL', 'http://fan-driver:8012')
    fan_ip = session.get("fan_ip", "192.168.4.1")

    if not frame_data:
        return

    try:
        async with aiohttp.ClientSession() as http:
            # Paso 1: Codificar a formato polar
            form = aiohttp.FormData()
            form.add_field('image', frame_data, filename='frame.png', content_type='image/png')

            async with http.post(
                f'{polar_encoder_url}/encode',
                data=form,
                timeout=aiohttp.ClientTimeout(total=1.0)
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Polar encoder retornó {resp.status}")
                    return
                polar_data = await resp.read()

            # Paso 2: Enviar al fan-driver
            form2 = aiohttp.FormData()
            form2.add_field('frame', polar_data, filename='frame.bin', content_type='application/octet-stream')

            async with http.post(
                f'{fan_driver_url}/stream/{fan_ip}',
                data=form2,
                timeout=aiohttp.ClientTimeout(total=1.0)
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Fan driver retornó {resp.status}")

    except aiohttp.ClientError as e:
        logger.warning(f"Error enviando al ventilador: {e}")
    except Exception as e:
        logger.error(f"Error inesperado en _send_to_fan: {e}")


def _create_sdp_answer(offer: str) -> str:
    """Crear respuesta SDP (placeholder)"""
    # TODO: Usar aiortc para generar SDP real
    return "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=holographic\r\nt=0 0\r\n"


def _generate_ice_candidates() -> list:
    """Generar candidatos ICE (placeholder)"""
    # TODO: Usar aiortc para generar candidatos reales
    return [
        {
            "candidate": "candidate:1 1 UDP 2122252543 192.168.1.100 50000 typ host",
            "sdpMid": "0",
            "sdpMLineIndex": 0
        }
    ]


# ============================================
# Endpoints adicionales para testing
# ============================================

@router.post("/test/send-frame")
async def test_send_frame(
    device_id: UUID,
    frame: bytes,
    db: AsyncSession = Depends(get_db)
):
    """Endpoint de prueba para enviar un frame individual"""
    # Verificar dispositivo
    result = await db.execute(
        text("SELECT * FROM core.devices WHERE id = :device_id"),
        {"device_id": str(device_id)}
    )
    device = result.fetchone()

    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # TODO: Procesar y enviar frame

    return {
        "status": "sent",
        "device_id": str(device_id),
        "frame_size": len(frame)
    }
