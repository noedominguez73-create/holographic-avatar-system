"""
Router para Modo 2: Recepcionista Virtual
Avatar que responde preguntas como recepcionista
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID, uuid4
from typing import Optional
import aiohttp
import base64
import logging

from ..db.database import get_db
from ..models import (
    ReceptionistStartRequest, ConversationInput, ConversationResponse,
    Session, SessionStatus, ModeType
)
from ..config import settings
from ..services.ai_client import AIClient

router = APIRouter()
logger = logging.getLogger(__name__)

# Sesiones activas (en producción usar Redis)
active_sessions = {}


@router.post("/start")
async def start_receptionist_mode(
    request: ReceptionistStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Iniciar modo recepcionista.

    Configura el avatar y el sistema conversacional.
    """
    # Verificar dispositivo
    result = await db.execute(
        text("SELECT * FROM core.devices WHERE id = :device_id"),
        {"device_id": str(request.device_id)}
    )
    device = result.fetchone()

    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Verificar avatar
    result = await db.execute(
        text("SELECT * FROM content.avatars WHERE id = :avatar_id"),
        {"avatar_id": str(request.avatar_id)}
    )
    avatar = result.fetchone()

    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar no encontrado")

    # Crear sesión
    result = await db.execute(
        text("""
            INSERT INTO conversations.sessions (device_id, mode, metadata)
            VALUES (:device_id, 'receptionist', :metadata)
            RETURNING id, started_at
        """),
        {
            "device_id": str(request.device_id),
            "metadata": f'{{"avatar_id": "{request.avatar_id}", "greeting": "{request.greeting_message}"}}'
        }
    )
    await db.commit()
    session_row = result.fetchone()

    session_id = session_row.id

    # Guardar en cache
    active_sessions[str(session_id)] = {
        "device_id": str(request.device_id),
        "avatar_id": str(request.avatar_id),
        "system_prompt": request.system_prompt or _default_receptionist_prompt(),
        "conversation_history": []
    }

    # Marcar dispositivo como ocupado
    await db.execute(
        text("UPDATE core.devices SET status = 'busy' WHERE id = :device_id"),
        {"device_id": str(request.device_id)}
    )
    await db.commit()

    # Reproducir saludo inicial
    greeting_response = await _generate_response(
        session_id=str(session_id),
        user_input=None,
        is_greeting=True,
        greeting_message=request.greeting_message
    )

    return {
        "session_id": str(session_id),
        "status": "started",
        "greeting": greeting_response
    }


@router.post("/conversation", response_model=ConversationResponse)
async def process_conversation(
    input_data: ConversationInput,
    db: AsyncSession = Depends(get_db)
):
    """
    Procesar input de conversación.

    Pipeline: Audio/Texto → ASR → LLM → TTS → Avatar
    """
    session_id = str(input_data.session_id)

    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Sesión no activa")

    session = active_sessions[session_id]

    # Obtener texto del usuario
    user_text = input_data.text

    if input_data.audio_base64 and not user_text:
        # Transcribir audio con ASR
        user_text = await _transcribe_audio(input_data.audio_base64)

    if not user_text:
        raise HTTPException(status_code=400, detail="Se requiere audio o texto")

    # Guardar mensaje del usuario en BD
    await db.execute(
        text("""
            INSERT INTO conversations.messages (session_id, role, content)
            VALUES (:session_id, 'user', :content)
        """),
        {"session_id": session_id, "content": user_text}
    )
    await db.commit()

    # Generar respuesta
    response = await _generate_response(
        session_id=session_id,
        user_input=user_text
    )

    # Guardar respuesta en BD
    await db.execute(
        text("""
            INSERT INTO conversations.messages (session_id, role, content, audio_url)
            VALUES (:session_id, 'assistant', :content, :audio_url)
        """),
        {
            "session_id": session_id,
            "content": response["response_text"],
            "audio_url": response.get("audio_url")
        }
    )
    await db.commit()

    return ConversationResponse(
        response_text=response["response_text"],
        audio_url=response.get("audio_url"),
        video_url=response.get("video_url"),
        intent=response.get("intent"),
        entities=response.get("entities")
    )


@router.post("/stop/{session_id}")
async def stop_receptionist_mode(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Detener modo recepcionista"""
    session_id_str = str(session_id)

    if session_id_str in active_sessions:
        session = active_sessions[session_id_str]

        # Liberar dispositivo
        await db.execute(
            text("UPDATE core.devices SET status = 'online' WHERE id = :device_id"),
            {"device_id": session["device_id"]}
        )

        del active_sessions[session_id_str]

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

    return {"status": "stopped", "session_id": session_id_str}


async def _transcribe_audio(audio_base64: str) -> str:
    """Transcribir audio usando ASR (Whisper)"""
    try:
        async with aiohttp.ClientSession() as session:
            audio_data = base64.b64decode(audio_base64)

            form_data = aiohttp.FormData()
            form_data.add_field('audio', audio_data, filename='audio.wav')

            async with session.post(
                f"{settings.linly_asr_url}/transcribe",
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("text", "")

    except Exception as e:
        logger.error(f"Error en ASR: {e}")

    return ""


async def _generate_response(
    session_id: str,
    user_input: Optional[str] = None,
    is_greeting: bool = False,
    greeting_message: str = None
) -> dict:
    """Generar respuesta usando LLM + TTS + Avatar"""

    session = active_sessions.get(session_id, {})

    if is_greeting:
        response_text = greeting_message or "¡Hola! ¿En qué puedo ayudarte?"
    else:
        # Llamar a LLM
        response_text = await _call_llm(
            user_input=user_input,
            system_prompt=session.get("system_prompt", ""),
            history=session.get("conversation_history", [])
        )

        # Actualizar historial
        session.setdefault("conversation_history", []).append({
            "role": "user",
            "content": user_input
        })
        session["conversation_history"].append({
            "role": "assistant",
            "content": response_text
        })

    # Generar audio con TTS
    audio_url = await _generate_tts(response_text)

    # Generar video de avatar
    video_url = await _generate_avatar_video(
        avatar_id=session.get("avatar_id"),
        audio_url=audio_url
    )

    return {
        "response_text": response_text,
        "audio_url": audio_url,
        "video_url": video_url
    }


async def _call_llm(user_input: str, system_prompt: str, history: list) -> str:
    """Llamar al LLM para generar respuesta"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{settings.linly_llm_url}/llm_response",
                json={
                    "question": user_input,
                    "system_prompt": system_prompt,
                    "history": history
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "Lo siento, no pude procesar tu pregunta.")

    except Exception as e:
        logger.error(f"Error en LLM: {e}")

    return "Lo siento, estoy teniendo problemas técnicos. ¿Podrías repetir tu pregunta?"


async def _generate_tts(text: str) -> Optional[str]:
    """Generar audio con TTS"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{settings.linly_tts_url}/tts_response",
                json={
                    "text": text,
                    "voice": settings.default_tts_voice
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("audio_url")

    except Exception as e:
        logger.error(f"Error en TTS: {e}")

    return None


async def _generate_avatar_video(avatar_id: str, audio_url: str) -> Optional[str]:
    """Generar video de avatar hablando"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{settings.linly_avatar_url}/talker_response",
                json={
                    "avatar_id": avatar_id,
                    "audio_url": audio_url
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("video_url")

    except Exception as e:
        logger.error(f"Error en Avatar: {e}")

    return None


def _default_receptionist_prompt() -> str:
    return """Eres un recepcionista virtual amigable y profesional.
Tu trabajo es dar la bienvenida a los visitantes, responder preguntas básicas
y dirigirlos al lugar correcto.

Reglas:
- Sé cordial y profesional
- Responde de forma concisa (máximo 2-3 oraciones)
- Si no sabes algo, sugiere hablar con un humano
- Usa un tono cálido pero formal
"""
