"""
Cliente para servicio TTS de Linly-Talker
"""
import aiohttp
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TTSResponse:
    audio_url: str
    audio_data: Optional[bytes]
    duration_seconds: float
    vtt_url: Optional[str]


class TTSClient:
    """Cliente para Text-to-Speech"""

    # Voces disponibles en Edge-TTS (español)
    VOICES_ES = {
        "dalia": "es-MX-DaliaNeural",      # México femenina
        "jorge": "es-MX-JorgeNeural",       # México masculina
        "elvira": "es-ES-ElviraNeural",     # España femenina
        "alvaro": "es-ES-AlvaroNeural",     # España masculina
    }

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=60)

    async def synthesize(
        self,
        text: str,
        voice: str = "es-MX-DaliaNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        engine: str = "edge-tts"
    ) -> TTSResponse:
        """
        Sintetizar voz a partir de texto.

        Args:
            text: Texto a convertir
            voice: Voz a usar (edge-tts voice name)
            rate: Velocidad (-50% a +100%)
            volume: Volumen (-50% a +100%)
            pitch: Tono (-50Hz a +50Hz)
            engine: Motor TTS

        Returns:
            TTSResponse con URL y datos del audio
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/tts_response",
                    json={
                        "text": text,
                        "voice": voice,
                        "rate": rate,
                        "volume": volume,
                        "pitch": pitch,
                        "engine": engine
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return TTSResponse(
                            audio_url=result.get("audio_url", ""),
                            audio_data=None,
                            duration_seconds=result.get("duration", 0),
                            vtt_url=result.get("vtt_url")
                        )
                    else:
                        error = await response.text()
                        logger.error(f"TTS error {response.status}: {error}")
                        raise Exception(f"TTS failed: {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"TTS connection error: {e}")
            raise

    async def synthesize_with_voice_clone(
        self,
        text: str,
        reference_audio_url: str,
        prompt_text: str = "",
        engine: str = "gpt-sovits"
    ) -> TTSResponse:
        """
        Sintetizar con clonación de voz (GPT-SoVITS).

        Args:
            text: Texto a convertir
            reference_audio_url: Audio de referencia para clonar
            prompt_text: Texto del audio de referencia
            engine: Motor (gpt-sovits, cosyvoice)
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/tts_response",
                    json={
                        "text": text,
                        "ref_audio": reference_audio_url,
                        "prompt_text": prompt_text,
                        "engine": engine
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return TTSResponse(
                            audio_url=result.get("audio_url", ""),
                            audio_data=None,
                            duration_seconds=result.get("duration", 0),
                            vtt_url=None
                        )
                    else:
                        raise Exception(f"TTS clone failed: {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"TTS clone error: {e}")
            raise

    async def change_model(self, engine: str, **kwargs) -> bool:
        """Cambiar motor TTS"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/tts_change_model",
                    json={"engine": engine, **kwargs}
                ) as response:
                    return response.status == 200
        except:
            return False

    async def list_voices(self) -> Dict[str, Any]:
        """Listar voces disponibles"""
        return {
            "edge-tts": self.VOICES_ES,
            "cosyvoice": ["default", "clone"],
            "gpt-sovits": ["custom"]
        }

    async def health_check(self) -> bool:
        """Verificar disponibilidad del servicio"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except:
            return False
