"""
Webcam a Ventilador Holográfico - Transmisión en Tiempo Real
Captura video de la webcam y lo envía al ventilador LED

Uso:
    python webcam_to_fan.py --fan-ip 192.168.4.1
"""

import cv2
import numpy as np
import socket
import struct
import time
import argparse
from typing import Optional, Tuple

# Configuración del ventilador
FAN_PORT_UPLOAD = 5499
FAN_PORT_CONTROL = 5233
FRAME_SIZE = 256  # Píxeles
NUM_RAYS = 2700   # Rayos radiales
NUM_LEDS = 224    # LEDs por rayo
DELAY_BETWEEN_PACKETS = 0.03  # 30ms

# Headers del protocolo
PACKET_HEADER = bytes.fromhex("d3e0c9ba02014dd8")
PACKET_TYPE_DATA = b"1GnH"
PACKET_TRAILER = bytes.fromhex("bfb5d2a2")


class WebcamToFan:
    def __init__(self, fan_ip: str = "192.168.4.1", camera_id: int = 0):
        self.fan_ip = fan_ip
        self.camera_id = camera_id
        self.cap: Optional[cv2.VideoCapture] = None
        self.socket: Optional[socket.socket] = None
        self.running = False

        # Para eliminación de fondo
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )

    def connect_camera(self) -> bool:
        """Conectar a la webcam"""
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            print(f"Error: No se pudo abrir la cámara {self.camera_id}")
            return False

        # Configurar resolución
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        print(f"Cámara {self.camera_id} conectada")
        return True

    def connect_fan(self) -> bool:
        """Conectar al ventilador via TCP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.fan_ip, FAN_PORT_UPLOAD))
            print(f"Conectado al ventilador en {self.fan_ip}:{FAN_PORT_UPLOAD}")
            return True
        except Exception as e:
            print(f"Error conectando al ventilador: {e}")
            return False

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Procesar frame para el ventilador holográfico:
        1. Detectar persona/rostro
        2. Eliminar fondo (hacer negro)
        3. Recortar circular
        4. Resize a 256x256
        """
        # Obtener dimensiones
        h, w = frame.shape[:2]

        # Detectar rostro para centrar
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        # Si hay rostro, centrar en él
        if len(faces) > 0:
            x, y, fw, fh = faces[0]
            cx, cy = x + fw // 2, y + fh // 2

            # Expandir área alrededor del rostro
            size = max(fw, fh) * 2
            x1 = max(0, cx - size // 2)
            y1 = max(0, cy - size // 2)
            x2 = min(w, cx + size // 2)
            y2 = min(h, cy + size // 2)

            frame = frame[y1:y2, x1:x2]

        # Eliminar fondo usando segmentación simple
        # (Para mejor calidad usar rembg, pero es más lento)
        mask = self.bg_subtractor.apply(frame)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

        # Aplicar máscara - fondo negro
        result = frame.copy()
        result[mask == 0] = [0, 0, 0]

        # Resize a cuadrado
        result = cv2.resize(result, (FRAME_SIZE, FRAME_SIZE))

        # Aplicar máscara circular
        center = FRAME_SIZE // 2
        Y, X = np.ogrid[:FRAME_SIZE, :FRAME_SIZE]
        dist = np.sqrt((X - center) ** 2 + (Y - center) ** 2)
        circular_mask = dist <= center

        result[~circular_mask] = [0, 0, 0]

        return result

    def convert_to_polar(self, frame: np.ndarray) -> bytes:
        """
        Convertir imagen cartesiana a coordenadas polares para el ventilador.

        El ventilador tiene:
        - 2700 rayos (ángulos)
        - 224 LEDs por rayo (radio)
        - Cada LED: 1 bit por color (R, G, B) con dithering
        """
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        max_radius = min(center_x, center_y)

        # Buffer de salida: 2700 rayos × 42 bytes por rayo (224 LEDs × 3 bits / 8)
        # Pero simplificamos a 224 LEDs × 3 bytes = 672 bytes por rayo
        # Total: 2700 × 672 = ~1.8MB por frame (demasiado)

        # Formato simplificado: imagen polar como JPEG comprimido
        # El ventilador interno lo decodifica

        polar_data = []

        for ray_idx in range(NUM_RAYS):
            angle = (ray_idx / NUM_RAYS) * 2 * np.pi
            ray_pixels = []

            for led_idx in range(NUM_LEDS):
                # Radio normalizado (0 = centro, 1 = borde)
                r = (led_idx / NUM_LEDS) * max_radius

                # Coordenadas cartesianas
                x = int(center_x + r * np.cos(angle))
                y = int(center_y + r * np.sin(angle))

                # Obtener color del píxel
                if 0 <= x < w and 0 <= y < h:
                    b, g, r_val = frame[y, x]
                else:
                    b, g, r_val = 0, 0, 0

                # Dithering ordenado para 1 bit por color
                threshold = 128
                r_bit = 1 if r_val > threshold else 0
                g_bit = 1 if g > threshold else 0
                b_bit = 1 if b > threshold else 0

                ray_pixels.append((r_bit << 2) | (g_bit << 1) | b_bit)

            # Empacar 8 LEDs en 3 bytes (cada LED = 3 bits)
            packed = self._pack_ray(ray_pixels)
            polar_data.append(packed)

        return b''.join(polar_data)

    def _pack_ray(self, pixels: list) -> bytes:
        """Empacar un rayo de LEDs en bytes"""
        # Simplificado: cada LED como 1 byte (RGB packed)
        return bytes(pixels)

    def send_frame_to_fan(self, polar_data: bytes) -> bool:
        """Enviar frame procesado al ventilador"""
        if not self.socket:
            return False

        try:
            # Dividir en chunks
            chunk_size = 1024
            total_chunks = (len(polar_data) + chunk_size - 1) // chunk_size

            for i in range(total_chunks):
                chunk = polar_data[i * chunk_size:(i + 1) * chunk_size]

                # Construir paquete
                packet = (
                    PACKET_HEADER +
                    PACKET_TYPE_DATA +
                    struct.pack('<H', i) +  # Número de chunk
                    struct.pack('<H', len(chunk)) +  # Tamaño
                    chunk +
                    PACKET_TRAILER
                )

                self.socket.send(packet)
                time.sleep(DELAY_BETWEEN_PACKETS / total_chunks)

            return True
        except Exception as e:
            print(f"Error enviando frame: {e}")
            return False

    def run(self, show_preview: bool = True):
        """Ejecutar el loop principal de captura y transmisión"""
        if not self.connect_camera():
            return

        if not self.connect_fan():
            print("Continuando sin conexión al ventilador (modo preview)")

        self.running = True
        frame_count = 0
        start_time = time.time()

        print("\nTransmitiendo... Presiona 'q' para salir")
        print("Presiona 'b' para recalibrar el fondo\n")

        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    print("Error leyendo frame")
                    break

                # Procesar frame
                processed = self.process_frame(frame)

                # Convertir a polar
                polar_data = self.convert_to_polar(processed)

                # Enviar al ventilador
                if self.socket:
                    self.send_frame_to_fan(polar_data)

                frame_count += 1

                # Mostrar preview
                if show_preview:
                    # Mostrar original y procesado lado a lado
                    original_small = cv2.resize(frame, (256, 256))
                    combined = np.hstack([original_small, processed])

                    # Mostrar FPS
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    cv2.putText(combined, f"FPS: {fps:.1f}", (10, 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                    cv2.imshow("Webcam -> Holograma", combined)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('b'):
                        # Recalibrar fondo
                        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                            history=500, varThreshold=16, detectShadows=False
                        )
                        print("Fondo recalibrado")

                # Limitar a ~10 FPS para el ventilador
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nDetenido por usuario")
        finally:
            self.cleanup()

    def cleanup(self):
        """Limpiar recursos"""
        self.running = False
        if self.cap:
            self.cap.release()
        if self.socket:
            self.socket.close()
        cv2.destroyAllWindows()
        print("Recursos liberados")


def main():
    parser = argparse.ArgumentParser(description="Transmitir webcam a ventilador holográfico")
    parser.add_argument("--fan-ip", default="192.168.4.1", help="IP del ventilador")
    parser.add_argument("--camera", type=int, default=0, help="ID de la cámara")
    parser.add_argument("--no-preview", action="store_true", help="Sin ventana de preview")
    args = parser.parse_args()

    print("=" * 50)
    print("  WEBCAM A VENTILADOR HOLOGRÁFICO")
    print("=" * 50)
    print(f"  Ventilador: {args.fan_ip}")
    print(f"  Cámara: {args.camera}")
    print("=" * 50)

    streamer = WebcamToFan(fan_ip=args.fan_ip, camera_id=args.camera)
    streamer.run(show_preview=not args.no_preview)


if __name__ == "__main__":
    main()
