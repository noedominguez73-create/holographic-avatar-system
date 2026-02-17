"""
Polar Encoder Service
Convierte imágenes cartesianas a formato polar para ventiladores LED holográficos
Basado en led-hologram-propeller de jnweiger
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response
import numpy as np
import cv2
import math
import io
import logging
from typing import List, Tuple

app = FastAPI(title="Polar Encoder Service", version="1.0.0")
logger = logging.getLogger(__name__)

# Configuración del ventilador
N_RAYS = 2700       # Posiciones angulares
N_LEDS = 224        # LEDs en el propeller
BYTES_PER_RAY = 42  # (224/2) * 3 / 8 bits
FRAME_PADDING = 1288  # Bytes de padding entre frames

# Tabla de dithering ordenado (2x12 matrix, 15 niveles)
DITHER_MATRIX = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 0
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 1
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],  # 2
    [1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0],  # 3
    [1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0],  # 4
    [1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0],  # 5
    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],  # 6
    [1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0],  # 7
    [1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0],  # 8
    [1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1],  # 9
    [1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],  # 10
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],  # 11
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # 12
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # 13
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # 14
]


class PolarEncoder:
    """Codificador de imágenes a formato polar para ventilador LED"""

    def __init__(self, n_rays: int = N_RAYS, n_leds: int = N_LEDS):
        self.n_rays = n_rays
        self.n_leds = n_leds
        self.bytes_per_ray = (n_leds // 2) * 3 // 8

        # Pre-calcular tabla de lookup
        self._build_lookup_table()

    def _build_lookup_table(self):
        """Pre-calcular coordenadas para conversión rápida"""
        self.lookup_x = np.zeros((self.n_rays, self.n_leds // 2), dtype=np.float32)
        self.lookup_y = np.zeros((self.n_rays, self.n_leds // 2), dtype=np.float32)

        for ray in range(self.n_rays):
            phi = 2 * math.pi * (self.n_rays - ray) / self.n_rays

            for led in range(self.n_leds // 2):
                # Radio normalizado (0 a 0.5, centro a borde)
                r = (led + 0.5) / self.n_leds

                self.lookup_x[ray, led] = 0.5 + r * math.cos(phi)
                self.lookup_y[ray, led] = 0.5 + r * math.sin(phi)

    def encode_frame(self, image: np.ndarray) -> bytes:
        """
        Convertir imagen RGB a formato binario del ventilador.

        Args:
            image: Imagen numpy BGR (OpenCV) de tamaño cuadrado

        Returns:
            Bytes en formato del ventilador
        """
        h, w = image.shape[:2]
        assert h == w, "Imagen debe ser cuadrada"

        # Convertir a RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image

        # Buffer de salida
        output = bytearray()

        for ray in range(self.n_rays):
            ray_bits = [0] * (self.n_leds // 2 * 3)  # R, G, B para cada LED

            for led in range(self.n_leds // 2):
                # Obtener coordenadas del pixel
                x = self.lookup_x[ray, led] * (w - 1)
                y = self.lookup_y[ray, led] * (h - 1)

                # Interpolación bilineal
                rgb = self._bilinear_sample(image_rgb, x, y)

                # Aplicar dithering ordenado
                r_bit = self._ordered_dither(x, y, rgb[0])
                g_bit = self._ordered_dither(x, y, rgb[1])
                b_bit = self._ordered_dither(x, y, rgb[2])

                # Guardar bits
                idx = led * 3
                ray_bits[idx] = r_bit
                ray_bits[idx + 1] = g_bit
                ray_bits[idx + 2] = b_bit

            # Empaquetar bits en bytes
            ray_bytes = self._pack_bits(ray_bits)
            output.extend(ray_bytes)

        return bytes(output)

    def _bilinear_sample(self, img: np.ndarray, x: float, y: float) -> Tuple[int, int, int]:
        """Muestreo bilineal de un pixel"""
        h, w = img.shape[:2]

        x0 = int(x)
        y0 = int(y)
        x1 = min(x0 + 1, w - 1)
        y1 = min(y0 + 1, h - 1)

        xd = x - x0
        yd = y - y0

        # Obtener los 4 pixels vecinos
        p00 = img[y0, x0].astype(float)
        p01 = img[y0, x1].astype(float)
        p10 = img[y1, x0].astype(float)
        p11 = img[y1, x1].astype(float)

        # Interpolación bilineal
        result = (
            p00 * (1 - xd) * (1 - yd) +
            p01 * xd * (1 - yd) +
            p10 * (1 - xd) * yd +
            p11 * xd * yd
        )

        return tuple(int(c) for c in result[:3])

    def _ordered_dither(self, x: float, y: float, value: int) -> int:
        """Aplicar dithering ordenado para convertir 8 bits a 1 bit"""
        # Extender rango de video [16..240] a [0..255]
        value = max(0, min(255, int((value - 16) * 255 / 224)))

        # Convertir a nivel de dithering (0-14)
        level = int(value / 17.01)
        level = max(0, min(14, level))

        # Obtener posición en matriz de dithering
        ix = int(x) % 2
        iy = int(y) % 12
        if ix == 1:
            iy = (iy + 6) % 12

        return DITHER_MATRIX[level][iy]

    def _pack_bits(self, bits: List[int]) -> bytes:
        """Empaquetar lista de bits en bytes"""
        # Asegurar múltiplo de 8
        while len(bits) % 8 != 0:
            bits.append(0)

        result = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                byte |= (bits[i + j] & 1) << (7 - j)
            result.append(byte)

        return bytes(result)

    def encode_animation(self, frames: List[np.ndarray]) -> bytes:
        """
        Codificar múltiples frames como animación.

        Args:
            frames: Lista de imágenes numpy

        Returns:
            Archivo .bin completo
        """
        # Header del archivo
        header = self._create_header(len(frames), is_gif=True)
        output = bytearray(header)

        # Codificar cada frame
        for frame in frames:
            frame_data = self.encode_frame(frame)
            output.extend(frame_data)

            # Padding entre frames
            output.extend(b'\x00' * FRAME_PADDING)

        return bytes(output)

    def _create_header(self, frame_count: int, is_gif: bool = True) -> bytes:
        """Crear header del archivo .bin"""
        header = bytearray(0x1000)  # 4KB header

        # Bytes mágicos
        header[0] = 0x00
        header[1] = 0x00
        header[2] = 0x00
        header[3] = 0x3c if is_gif else 0x01
        header[4] = 0x18

        # El resto se llena con valores aleatorios (como hace el original)
        import random
        for i in range(5, 0x1000):
            header[i] = random.randint(0, 255)

        return bytes(header)


# Instancia global del encoder
encoder = PolarEncoder()


@app.post("/encode")
async def encode_frame(
    image: UploadFile = File(...),
    n_rays: int = N_RAYS,
    n_leds: int = N_LEDS
):
    """Codificar una imagen a formato polar"""
    image_data = await image.read()
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    # Redimensionar si no es cuadrada
    h, w = img.shape[:2]
    if h != w:
        size = min(h, w)
        img = img[:size, :size]

    # Codificar
    encoded = encoder.encode_frame(img)

    return Response(
        content=encoded,
        media_type="application/octet-stream",
        headers={"X-Frame-Size": str(len(encoded))}
    )


@app.post("/encode-animation")
async def encode_animation(
    images: List[UploadFile] = File(...)
):
    """Codificar múltiples imágenes como animación .bin"""
    frames = []

    for image_file in images:
        image_data = await image_file.read()
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is not None:
            # Redimensionar si necesario
            h, w = img.shape[:2]
            if h != w:
                size = min(h, w)
                img = img[:size, :size]
            frames.append(img)

    if not frames:
        raise HTTPException(status_code=400, detail="No valid images")

    # Codificar animación
    bin_data = encoder.encode_animation(frames)

    return Response(
        content=bin_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename=animation.bin",
            "X-Frame-Count": str(len(frames)),
            "X-File-Size": str(len(bin_data))
        }
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
