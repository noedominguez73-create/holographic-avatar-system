"""
Wrapper para el encoder polar de led-hologram-propeller
"""
import sys
from pathlib import Path
from typing import List, Optional
import numpy as np

# Agregar paths a los repos
LED_HOLOGRAM_PATH = Path("C:/avatar ventilador/led-hologram-propeller/src")
POLAR_ENCODER_PATH = Path("C:/avatar ventilador/holographic-system/services/polar-encoder")

if LED_HOLOGRAM_PATH.exists():
    sys.path.insert(0, str(LED_HOLOGRAM_PATH))
if POLAR_ENCODER_PATH.exists():
    sys.path.insert(0, str(POLAR_ENCODER_PATH))


class PolarEncoderWrapper:
    """
    Wrapper para usar el encoder polar del repositorio led-hologram-propeller.

    Si el repo original no está disponible, usa implementación fallback.
    """

    def __init__(self, n_rays: int = 2700, n_leds: int = 224):
        self.n_rays = n_rays
        self.n_leds = n_leds
        self._original_encoder = None

        # Intentar cargar encoder original
        try:
            from encode_polar_bin import encode_polar_bin
            self._original_encoder = encode_polar_bin
        except ImportError:
            pass

    def encode_image(self, image_path: str) -> bytes:
        """
        Codificar imagen a formato .bin del ventilador.

        Args:
            image_path: Ruta a la imagen

        Returns:
            Datos binarios para el ventilador
        """
        if self._original_encoder:
            return self._use_original_encoder(image_path)
        else:
            return self._fallback_encode(image_path)

    def _use_original_encoder(self, image_path: str) -> bytes:
        """Usar encoder del repo original"""
        from PIL import Image
        im = Image.open(image_path)
        return self._original_encoder(im)

    def _fallback_encode(self, image_path: str) -> bytes:
        """Encoder de respaldo si el original no está disponible"""
        import cv2

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"No se pudo cargar imagen: {image_path}")

        # Importar encoder de nuestro servicio
        from main import PolarEncoder
        encoder = PolarEncoder(self.n_rays, self.n_leds)
        return encoder.encode_frame(img)

    def encode_images(self, image_paths: List[str]) -> bytes:
        """
        Codificar múltiples imágenes como animación.

        Args:
            image_paths: Lista de rutas a imágenes

        Returns:
            Archivo .bin completo
        """
        frames = []

        for path in image_paths:
            import cv2
            img = cv2.imread(path)
            if img is not None:
                frames.append(img)

        if not frames:
            raise ValueError("No se cargaron imágenes válidas")

        from main import PolarEncoder
        encoder = PolarEncoder(self.n_rays, self.n_leds)
        return encoder.encode_animation(frames)

    def encode_video(self, video_path: str, fps: int = 10) -> bytes:
        """
        Codificar video a formato .bin.

        Args:
            video_path: Ruta al video
            fps: FPS objetivo (el ventilador soporta ~10)

        Returns:
            Archivo .bin
        """
        import cv2

        cap = cv2.VideoCapture(video_path)
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_skip = max(1, int(original_fps / fps))

        frames = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_skip == 0:
                # Hacer cuadrada
                h, w = frame.shape[:2]
                size = min(h, w)
                y = (h - size) // 2
                x = (w - size) // 2
                frame = frame[y:y+size, x:x+size]
                frames.append(frame)

            frame_count += 1

        cap.release()

        if not frames:
            raise ValueError("No se extrajeron frames del video")

        from main import PolarEncoder
        encoder = PolarEncoder(self.n_rays, self.n_leds)
        return encoder.encode_animation(frames)
