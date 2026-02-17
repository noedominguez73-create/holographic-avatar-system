"""
Cliente para servicio ASR de Linly-Talker
"""
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ASRClient:
    """Cliente para Automatic Speech Recognition"""

    def __init__(self, base_url: str = "http://localhost:8004"):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "es",
        model: str = "whisper-base"
    ) -> str:
        """
        Transcribir audio a texto.

        Args:
            audio_data: Audio en bytes (WAV, MP3, etc.)
            language: Código de idioma
            model: Modelo ASR a usar

        Returns:
            Texto transcrito
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                form_data = aiohttp.FormData()
                form_data.add_field('audio', audio_data, filename='audio.wav')
                form_data.add_field('language', language)
                form_data.add_field('model', model)

                async with session.post(
                    f"{self.base_url}/asr",
                    data=form_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("text", "")
                    else:
                        error = await response.text()
                        logger.error(f"ASR error {response.status}: {error}")
                        return ""

        except aiohttp.ClientError as e:
            logger.error(f"ASR connection error: {e}")
            return ""

    async def transcribe_streaming(self, audio_stream):
        """Transcripción en streaming (para tiempo real)"""
        # TODO: Implementar streaming ASR
        pass

    async def change_model(self, model: str) -> bool:
        """Cambiar modelo ASR"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/asr_change_model",
                    json={"model": model}
                ) as response:
                    return response.status == 200
        except:
            return False

    async def health_check(self) -> bool:
        """Verificar disponibilidad del servicio"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except:
            return False
