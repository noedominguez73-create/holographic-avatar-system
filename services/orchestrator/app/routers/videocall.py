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

    1. Decodificar imagen
    2. Detectar rostro
    3. Eliminar fondo (negro)
    4. Recortar circular
    5. Convertir a formato polar
    """
    import cv2
    import numpy as np

    # Decodificar
    nparr = np.frombuffer(frame_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return b''

    # TODO: Llamar a Frame Processor service
    # Por ahora hacer procesamiento básico

    # Resize a 256x256
    frame = cv2.resize(frame, (256, 256))

    # Hacer fondo negro (placeholder - debería usar rembg)
    # Por ahora solo retornar el frame

    # Codificar de vuelta
    _, encoded = cv2.imencode('.jpg', frame)
    return encoded.tobytes()


async def _send_to_fan(frame_data: bytes, session: dict):
    """Enviar frame procesado al ventilador"""
    # TODO: Llamar a Fan Driver service
    # Por ahora solo simular delay
    await asyncio.sleep(0.033)  # ~30 FPS


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
