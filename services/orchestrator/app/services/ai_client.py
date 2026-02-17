"""
Cliente unificado para servicios de AI
Integra FasterLivePortrait, Linly-Talker (ASR, TTS, LLM, Avatar)
"""
import aiohttp
import base64
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class AnimationResult:
    video_url: str
    bin_file_url: Optional[str]
    duration_seconds: float
    frame_count: int


@dataclass
class TTSResult:
    audio_url: str
    duration_seconds: float
    vtt_url: Optional[str]


@dataclass
class AvatarResult:
    video_url: str
    audio_url: str
    duration_seconds: float


class AIClient:
    """Cliente unificado para todos los servicios de AI"""

    def __init__(self):
        self.faster_liveportrait_url = settings.faster_liveportrait_url
        self.asr_url = settings.linly_asr_url
        self.tts_url = settings.linly_tts_url
        self.llm_url = settings.linly_llm_url
        self.avatar_url = settings.linly_avatar_url
        self.timeout = aiohttp.ClientTimeout(total=120)

    # ============================================
    # FasterLivePortrait - Animación de fotos
    # ============================================

    async def generate_animation(
        self,
        source_image: bytes,
        driving_video: Optional[bytes] = None,
        driving_pickle: Optional[bytes] = None,
        is_animal: bool = False,
        relative_motion: bool = True,
        do_crop: bool = True,
        stitching: bool = True,
        duration_seconds: float = 5.0
    ) -> AnimationResult:
        """
        Generar video animado a partir de imagen estática.

        Args:
            source_image: Imagen fuente en bytes
            driving_video: Video de movimiento (opcional)
            driving_pickle: Preset de movimiento pkl (opcional)
            is_animal: True si es animal
            relative_motion: Usar movimiento relativo
            do_crop: Recortar rostro
            stitching: Aplicar stitching
            duration_seconds: Duración deseada

        Returns:
            AnimationResult con URLs de video y .bin
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                form_data = aiohttp.FormData()
                form_data.add_field('source_image', source_image, filename='source.jpg')

                if driving_video:
                    form_data.add_field('driving_video', driving_video, filename='driver.mp4')
                    form_data.add_field('flag_pickle', 'false')
                elif driving_pickle:
                    form_data.add_field('driving_pickle', driving_pickle, filename='driver.pkl')
                    form_data.add_field('flag_pickle', 'true')

                form_data.add_field('flag_is_animal', str(is_animal).lower())
                form_data.add_field('flag_relative_input', str(relative_motion).lower())
                form_data.add_field('flag_do_crop_input', str(do_crop).lower())
                form_data.add_field('flag_stitching', str(stitching).lower())

                async with session.post(
                    f"{self.faster_liveportrait_url}/predict/",
                    data=form_data
                ) as response:
                    if response.status == 200:
                        # Recibir ZIP con videos
                        data = await response.read()
                        # TODO: Extraer videos del ZIP y guardar

                        return AnimationResult(
                            video_url="/generated/animation.mp4",
                            bin_file_url=None,
                            duration_seconds=duration_seconds,
                            frame_count=int(duration_seconds * 25)
                        )
                    else:
                        error = await response.text()
                        logger.error(f"FasterLivePortrait error: {response.status} - {error}")
                        raise Exception(f"Animation failed: {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"Error conectando a FasterLivePortrait: {e}")
            raise

    # ============================================
    # ASR - Reconocimiento de voz
    # ============================================

    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = "es"
    ) -> str:
        """
        Transcribir audio a texto usando Whisper.

        Args:
            audio_data: Audio en bytes (WAV)
            language: Código de idioma

        Returns:
            Texto transcrito
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                form_data = aiohttp.FormData()
                form_data.add_field('audio', audio_data, filename='audio.wav')
                form_data.add_field('language', language)

                async with session.post(
                    f"{self.asr_url}/transcribe",
                    data=form_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("text", "")
                    else:
                        logger.error(f"ASR error: {response.status}")
                        return ""

        except aiohttp.ClientError as e:
            logger.error(f"Error conectando a ASR: {e}")
            return ""

    # ============================================
    # TTS - Síntesis de voz
    # ============================================

    async def synthesize_speech(
        self,
        text: str,
        voice: str = "es-MX-DaliaNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        engine: str = "edge-tts"
    ) -> TTSResult:
        """
        Sintetizar voz a partir de texto.

        Args:
            text: Texto a convertir
            voice: Voz a usar
            rate: Velocidad
            volume: Volumen
            engine: Motor TTS (edge-tts, cosyvoice, gpt-sovits)

        Returns:
            TTSResult con URL del audio
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.tts_url}/tts_response",
                    json={
                        "text": text,
                        "voice": voice,
                        "rate": rate,
                        "volume": volume,
                        "engine": engine
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return TTSResult(
                            audio_url=result.get("audio_url", ""),
                            duration_seconds=result.get("duration", 0),
                            vtt_url=result.get("vtt_url")
                        )
                    else:
                        logger.error(f"TTS error: {response.status}")
                        raise Exception(f"TTS failed: {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"Error conectando a TTS: {e}")
            raise

    # ============================================
    # LLM - Modelo de lenguaje
    # ============================================

    async def generate_response(
        self,
        question: str,
        system_prompt: str = "",
        history: List[Dict[str, str]] = None,
        model: str = "Qwen"
    ) -> str:
        """
        Generar respuesta usando LLM.

        Args:
            question: Pregunta del usuario
            system_prompt: Prompt del sistema
            history: Historial de conversación
            model: Modelo a usar

        Returns:
            Respuesta generada
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.llm_url}/llm_response",
                    json={
                        "question": question,
                        "system_prompt": system_prompt,
                        "history": history or [],
                        "model": model
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "")
                    else:
                        logger.error(f"LLM error: {response.status}")
                        return "Lo siento, no pude generar una respuesta."

        except aiohttp.ClientError as e:
            logger.error(f"Error conectando a LLM: {e}")
            return "Lo siento, estoy teniendo problemas técnicos."

    # ============================================
    # Avatar - Generación de video hablante
    # ============================================

    async def generate_talking_avatar(
        self,
        avatar_image_url: str,
        audio_url: str,
        engine: str = "sadtalker",
        preprocess: str = "crop"
    ) -> AvatarResult:
        """
        Generar video de avatar hablando.

        Args:
            avatar_image_url: URL de imagen del avatar
            audio_url: URL del audio
            engine: Motor (sadtalker, wav2lip, musetalk)
            preprocess: Preprocesamiento (crop, full)

        Returns:
            AvatarResult con URL del video
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.avatar_url}/talker_response",
                    json={
                        "source_image": avatar_image_url,
                        "driven_audio": audio_url,
                        "engine": engine,
                        "preprocess": preprocess
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return AvatarResult(
                            video_url=result.get("video_url", ""),
                            audio_url=audio_url,
                            duration_seconds=result.get("duration", 0)
                        )
                    else:
                        logger.error(f"Avatar error: {response.status}")
                        raise Exception(f"Avatar failed: {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"Error conectando a Avatar: {e}")
            raise

    # ============================================
    # Pipeline completo de conversación
    # ============================================

    async def conversation_pipeline(
        self,
        audio_input: Optional[bytes] = None,
        text_input: Optional[str] = None,
        avatar_image_url: str = None,
        system_prompt: str = "",
        history: List[Dict[str, str]] = None,
        voice: str = "es-MX-DaliaNeural"
    ) -> Dict[str, Any]:
        """
        Pipeline completo: Audio/Texto → ASR → LLM → TTS → Avatar

        Returns:
            Dict con response_text, audio_url, video_url
        """
        # 1. Transcribir audio si es necesario
        if audio_input and not text_input:
            text_input = await self.transcribe_audio(audio_input)

        if not text_input:
            return {"error": "No input provided"}

        # 2. Generar respuesta con LLM
        response_text = await self.generate_response(
            question=text_input,
            system_prompt=system_prompt,
            history=history
        )

        # 3. Sintetizar voz
        tts_result = await self.synthesize_speech(
            text=response_text,
            voice=voice
        )

        # 4. Generar video de avatar (si hay imagen)
        video_url = None
        if avatar_image_url and tts_result.audio_url:
            avatar_result = await self.generate_talking_avatar(
                avatar_image_url=avatar_image_url,
                audio_url=tts_result.audio_url
            )
            video_url = avatar_result.video_url

        return {
            "input_text": text_input,
            "response_text": response_text,
            "audio_url": tts_result.audio_url,
            "video_url": video_url,
            "duration_seconds": tts_result.duration_seconds
        }


# Instancia global
ai_client = AIClient()
