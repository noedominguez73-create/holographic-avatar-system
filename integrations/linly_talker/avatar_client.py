"""
Cliente para servicio Avatar de Linly-Talker
"""
import aiohttp
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AvatarResponse:
    video_url: str
    duration_seconds: float
    frame_count: int


class AvatarClient:
    """Cliente para generación de video de avatar hablante"""

    # Motores disponibles
    ENGINES = {
        "sadtalker": "SadTalker",
        "wav2lip": "Wav2Lip",
        "wav2lipv2": "Wav2Lipv2",
        "musetalk": "MuseTalk"
    }

    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=120)

    async def generate(
        self,
        source_image_url: str,
        audio_url: str,
        engine: str = "sadtalker",
        preprocess: str = "crop",
        still_mode: bool = False,
        expression_scale: float = 1.0
    ) -> AvatarResponse:
        """
        Generar video de avatar hablando.

        Args:
            source_image_url: URL de imagen del avatar
            audio_url: URL del audio
            engine: Motor (sadtalker, wav2lip, musetalk)
            preprocess: Preprocesamiento (crop, full, resize)
            still_mode: Solo sincronización labial, sin movimiento de cabeza
            expression_scale: Intensidad de expresiones

        Returns:
            AvatarResponse con URL del video
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/talker_response",
                    json={
                        "source_image": source_image_url,
                        "driven_audio": audio_url,
                        "engine": engine,
                        "preprocess": preprocess,
                        "still_mode": still_mode,
                        "expression_scale": expression_scale
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return AvatarResponse(
                            video_url=result.get("video_url", ""),
                            duration_seconds=result.get("duration", 0),
                            frame_count=result.get("frame_count", 0)
                        )
                    else:
                        error = await response.text()
                        logger.error(f"Avatar error {response.status}: {error}")
                        raise Exception(f"Avatar failed: {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"Avatar connection error: {e}")
            raise

    async def generate_with_video_reference(
        self,
        source_video_url: str,
        audio_url: str,
        engine: str = "musetalk",
        bbox_shift: int = 0,
        batch_size: int = 4
    ) -> AvatarResponse:
        """
        Generar usando video de referencia (MuseTalk).

        Args:
            source_video_url: URL de video de referencia
            audio_url: URL del audio
            engine: Motor (musetalk recomendado)
            bbox_shift: Ajuste del bounding box
            batch_size: Tamaño de batch
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/talker_response",
                    json={
                        "source_video": source_video_url,
                        "driven_audio": audio_url,
                        "engine": engine,
                        "bbox_shift": bbox_shift,
                        "batch_size": batch_size
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return AvatarResponse(
                            video_url=result.get("video_url", ""),
                            duration_seconds=result.get("duration", 0),
                            frame_count=result.get("frame_count", 0)
                        )
                    else:
                        raise Exception(f"Avatar video failed: {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"Avatar video error: {e}")
            raise

    async def change_model(self, engine: str) -> bool:
        """Cambiar motor de avatar"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/talker_change_model",
                    json={"engine": engine}
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
