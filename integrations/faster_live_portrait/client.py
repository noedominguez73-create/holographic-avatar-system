"""
Cliente para FasterLivePortrait API
"""
import aiohttp
import zipfile
import io
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FasterLivePortraitClient:
    """Cliente para interactuar con FasterLivePortrait API"""

    def __init__(self, base_url: str = "http://localhost:9871"):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=120)

    async def predict(
        self,
        source_image: bytes,
        driving_video: Optional[bytes] = None,
        driving_pickle: Optional[bytes] = None,
        config: dict = None
    ) -> Tuple[bytes, bytes]:
        """
        Generar animación.

        Args:
            source_image: Imagen fuente (bytes)
            driving_video: Video de movimiento (bytes)
            driving_pickle: Preset .pkl (bytes)
            config: Configuración adicional

        Returns:
            Tuple[video_crop, video_org] como bytes
        """
        config = config or {}

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            form_data = aiohttp.FormData()

            # Imagen fuente (requerida)
            form_data.add_field(
                'source_image',
                source_image,
                filename='source.jpg',
                content_type='image/jpeg'
            )

            # Driver
            if driving_pickle:
                form_data.add_field(
                    'driving_pickle',
                    driving_pickle,
                    filename='driver.pkl'
                )
                form_data.add_field('flag_pickle', 'true')
            elif driving_video:
                form_data.add_field(
                    'driving_video',
                    driving_video,
                    filename='driver.mp4',
                    content_type='video/mp4'
                )
                form_data.add_field('flag_pickle', 'false')

            # Configuración
            form_data.add_field('flag_is_animal', str(config.get('is_animal', False)).lower())
            form_data.add_field('flag_relative_input', str(config.get('relative_motion', True)).lower())
            form_data.add_field('flag_do_crop_input', str(config.get('do_crop', True)).lower())
            form_data.add_field('flag_remap_input', str(config.get('remap', True)).lower())
            form_data.add_field('flag_stitching', str(config.get('stitching', True)).lower())
            form_data.add_field('flag_crop_driving_video_input', str(config.get('crop_driving', True)).lower())
            form_data.add_field('driving_multiplier', str(config.get('multiplier', 1.0)))
            form_data.add_field('scale', str(config.get('scale', 2.3)))
            form_data.add_field('vx_ratio', str(config.get('vx_ratio', 0.0)))
            form_data.add_field('vy_ratio', str(config.get('vy_ratio', -0.125)))

            async with session.post(
                f"{self.base_url}/predict/",
                data=form_data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"FasterLivePortrait error {response.status}: {error_text}")

                # La respuesta es un ZIP
                zip_data = await response.read()
                return self._extract_videos_from_zip(zip_data)

    def _extract_videos_from_zip(self, zip_data: bytes) -> Tuple[bytes, bytes]:
        """Extraer videos del ZIP de respuesta"""
        video_crop = b''
        video_org = b''

        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            for name in zf.namelist():
                if name.endswith('-crop.mp4'):
                    video_crop = zf.read(name)
                elif name.endswith('-org.mp4'):
                    video_org = zf.read(name)

        return video_crop, video_org

    async def health_check(self) -> bool:
        """Verificar si el servicio está disponible"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.base_url}/") as response:
                    return response.status == 200
        except:
            return False


class PresetManager:
    """Gestiona presets de movimiento (.pkl) para animaciones"""

    PRESETS = {
        "natural": "natural_movement.pkl",
        "breathing": "breathing.pkl",
        "greeting": "greeting.pkl",
        "talking": "talking_loop.pkl",
        "nodding": "nodding.pkl"
    }

    def __init__(self, presets_dir: str = "assets/presets"):
        self.presets_dir = Path(presets_dir)

    def get_preset(self, name: str) -> Optional[bytes]:
        """Obtener datos de un preset por nombre"""
        if name not in self.PRESETS:
            return None

        preset_path = self.presets_dir / self.PRESETS[name]
        if not preset_path.exists():
            logger.warning(f"Preset file not found: {preset_path}")
            return None

        return preset_path.read_bytes()

    def list_presets(self) -> list:
        """Listar presets disponibles"""
        return list(self.PRESETS.keys())
