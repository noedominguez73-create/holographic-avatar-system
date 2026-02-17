"""
Frame Processor Service
Procesa frames de video para optimizarlos para el ventilador holográfico
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response
import cv2
import numpy as np
from PIL import Image
import io
import logging

app = FastAPI(title="Frame Processor Service", version="1.0.0")
logger = logging.getLogger(__name__)


@app.post("/process")
async def process_frame(
    frame: UploadFile = File(...),
    target_size: int = 256,
    circular_crop: bool = True,
    remove_background: bool = True,
    brightness_boost: float = 1.2,
    contrast_boost: float = 1.1
):
    """
    Procesar un frame para el ventilador holográfico.

    1. Redimensionar a tamaño objetivo
    2. Eliminar fondo (negro puro)
    3. Recortar circular
    4. Ajustar brillo/contraste
    """
    # Leer imagen
    image_data = await frame.read()
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    # Procesar
    processed = process_for_hologram(
        img,
        target_size=target_size,
        circular=circular_crop,
        remove_bg=remove_background,
        brightness=brightness_boost,
        contrast=contrast_boost
    )

    # Codificar resultado
    _, encoded = cv2.imencode('.png', processed)
    return Response(content=encoded.tobytes(), media_type="image/png")


@app.post("/process-batch")
async def process_batch(
    frames: list[UploadFile] = File(...),
    target_size: int = 256
):
    """Procesar múltiples frames en batch"""
    results = []

    for frame in frames:
        image_data = await frame.read()
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is not None:
            processed = process_for_hologram(img, target_size)
            _, encoded = cv2.imencode('.png', processed)
            results.append(encoded.tobytes())

    return {"processed_count": len(results)}


@app.post("/extract-frames")
async def extract_frames_from_video(
    video: UploadFile = File(...),
    fps: int = 10,
    target_size: int = 256
):
    """Extraer y procesar frames de un video"""
    # Guardar video temporalmente
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(await video.read())
        tmp_path = tmp.name

    try:
        frames = extract_and_process_video(tmp_path, fps, target_size)
        return {
            "frame_count": len(frames),
            "fps": fps,
            "total_duration": len(frames) / fps
        }
    finally:
        os.unlink(tmp_path)


def process_for_hologram(
    img: np.ndarray,
    target_size: int = 256,
    circular: bool = True,
    remove_bg: bool = True,
    brightness: float = 1.2,
    contrast: float = 1.1
) -> np.ndarray:
    """
    Procesar imagen para display holográfico.

    Args:
        img: Imagen BGR de OpenCV
        target_size: Tamaño objetivo (cuadrado)
        circular: Aplicar máscara circular
        remove_bg: Eliminar fondo (hacer negro)
        brightness: Factor de brillo
        contrast: Factor de contraste

    Returns:
        Imagen procesada
    """
    # 1. Redimensionar manteniendo aspecto
    h, w = img.shape[:2]
    if h != w:
        # Hacer cuadrado
        size = min(h, w)
        y_start = (h - size) // 2
        x_start = (w - size) // 2
        img = img[y_start:y_start+size, x_start:x_start+size]

    img = cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)

    # 2. Eliminar fondo (simplificado - en producción usar rembg)
    if remove_bg:
        img = remove_background_simple(img)

    # 3. Ajustar brillo y contraste
    img = adjust_brightness_contrast(img, brightness, contrast)

    # 4. Aplicar máscara circular
    if circular:
        img = apply_circular_mask(img)

    return img


def remove_background_simple(img: np.ndarray) -> np.ndarray:
    """
    Eliminación simple de fondo (placeholder).
    En producción usar rembg o similar.
    """
    # Convertir a HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Crear máscara basada en saturación (detectar regiones con color)
    _, mask = cv2.threshold(hsv[:, :, 1], 30, 255, cv2.THRESH_BINARY)

    # Aplicar operaciones morfológicas para limpiar
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # Dilatar un poco la máscara
    mask = cv2.dilate(mask, kernel, iterations=2)

    # Aplicar máscara
    result = img.copy()
    result[mask == 0] = [0, 0, 0]  # Negro puro

    return result


def adjust_brightness_contrast(
    img: np.ndarray,
    brightness: float = 1.0,
    contrast: float = 1.0
) -> np.ndarray:
    """Ajustar brillo y contraste"""
    # Convertir a float
    img_float = img.astype(np.float32)

    # Aplicar contraste (centrado en 127.5)
    img_float = (img_float - 127.5) * contrast + 127.5

    # Aplicar brillo
    img_float = img_float * brightness

    # Clipear y convertir de vuelta
    img_float = np.clip(img_float, 0, 255)
    return img_float.astype(np.uint8)


def apply_circular_mask(img: np.ndarray) -> np.ndarray:
    """Aplicar máscara circular (fondo negro fuera del círculo)"""
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    radius = min(w, h) // 2

    # Crear máscara circular
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, center, radius, 255, -1)

    # Aplicar máscara
    result = img.copy()
    result[mask == 0] = [0, 0, 0]

    return result


def extract_and_process_video(
    video_path: str,
    target_fps: int = 10,
    target_size: int = 256
) -> list:
    """Extraer frames de video y procesarlos"""
    cap = cv2.VideoCapture(video_path)
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_skip = max(1, int(original_fps / target_fps))

    frames = []
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_skip == 0:
            processed = process_for_hologram(frame, target_size)
            frames.append(processed)

        frame_count += 1

    cap.release()
    return frames


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
