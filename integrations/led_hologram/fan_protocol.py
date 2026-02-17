"""
Protocolo de comunicación con ventilador holográfico
Basado en reverse-engineering de led-hologram-propeller
"""
import socket
import struct
import asyncio
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FanProtocol:
    """
    Protocolo TCP para comunicación con ventiladores holográficos.

    Puertos:
    - 5499: Upload de archivos .bin
    - 5233: Control (play, pause, status, delete)
    """

    # Constantes del protocolo
    UPLOAD_PORT = 5499
    CONTROL_PORT = 5233
    DEFAULT_IP = "192.168.4.1"

    PACKET_SIZE = 1460
    PACKET_DELAY = 0.03  # 30ms mínimo entre paquetes

    # Headers y trailers
    HEADER = bytes.fromhex("d3e0c9ba02014dd8")
    TYPE_NAME = b"0AgQ"
    TYPE_DATA = b"1GnH"
    TYPE_END = b"1AfF"
    TRAILER = bytes.fromhex("bfb5d2a2")

    CONTROL_HEADER = bytes.fromhex("c0eeb7c9baa3020000000014cc")

    def __init__(self, ip: str = None):
        self.ip = ip or self.DEFAULT_IP
        self._upload_socket: Optional[socket.socket] = None
        self._control_socket: Optional[socket.socket] = None

    async def connect_upload(self) -> bool:
        """Conectar al puerto de upload"""
        try:
            self._upload_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._upload_socket.settimeout(10)
            self._upload_socket.connect((self.ip, self.UPLOAD_PORT))
            logger.info(f"Conectado a {self.ip}:{self.UPLOAD_PORT}")
            return True
        except Exception as e:
            logger.error(f"Error conectando: {e}")
            return False

    def disconnect_upload(self):
        """Desconectar upload"""
        if self._upload_socket:
            self._upload_socket.close()
            self._upload_socket = None

    async def upload_bin(self, filename: str, data: bytes) -> bool:
        """
        Subir archivo .bin al ventilador.

        El archivo se guarda en la SD card del ventilador y se reproduce.

        Args:
            filename: Nombre del archivo (max 99 caracteres, debe terminar en .bin)
            data: Contenido del archivo

        Returns:
            True si éxito
        """
        if not self._upload_socket:
            if not await self.connect_upload():
                return False

        try:
            # Asegurar extensión .bin
            if not filename.endswith('.bin'):
                filename = filename + '.bin'

            filename_bytes = filename.encode()[:99]
            file_size = len(data)

            # Paquete 1: Nombre y tamaño
            name_packet = (
                self.HEADER +
                self.TYPE_NAME +
                struct.pack(">I", file_size) +
                filename_bytes +
                self.TRAILER
            )

            self._upload_socket.send(name_packet)
            await asyncio.sleep(self.PACKET_DELAY)

            # Paquetes de datos
            payload_size = self.PACKET_SIZE - len(self.HEADER) - len(self.TYPE_DATA) - len(self.TRAILER)

            offset = 0
            packet_count = 0

            while offset < len(data):
                chunk = data[offset:offset + payload_size]

                # Padding si necesario
                if len(chunk) < payload_size:
                    chunk += b'\x00' * (payload_size - len(chunk))

                packet = self.HEADER + self.TYPE_DATA + chunk + self.TRAILER
                self._upload_socket.send(packet)
                await asyncio.sleep(self.PACKET_DELAY)

                offset += payload_size
                packet_count += 1

                if packet_count % 100 == 0:
                    logger.debug(f"Enviados {packet_count} paquetes...")

            # Paquete final
            end_packet = self.HEADER + self.TYPE_END + self.TRAILER
            self._upload_socket.send(end_packet)

            logger.info(f"Upload completo: {filename} ({file_size} bytes, {packet_count} paquetes)")
            return True

        except Exception as e:
            logger.error(f"Error en upload: {e}")
            return False

    async def send_control(self, command: str) -> Tuple[bool, Optional[bytes]]:
        """
        Enviar comando de control.

        Commands:
        - play: Reproducir
        - pause: Pausar
        - status: Obtener estado
        - delete: Eliminar archivo actual

        Returns:
            (éxito, respuesta)
        """
        commands = {
            "pause": b"34",
            "play": b"35",
            "status": b"38",
            "delete": b"39"
        }

        if command not in commands:
            logger.error(f"Comando desconocido: {command}")
            return False, None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.ip, self.CONTROL_PORT))

            # Construir paquete
            if command == "delete":
                cmd_packet = self.CONTROL_HEADER + commands[command] + b"lfj00bfb5d2a2"
            else:
                cmd_packet = self.CONTROL_HEADER + commands[command] + b"lfhbfb5d2a2"

            sock.send(cmd_packet)

            # Esperar respuesta para status
            response = None
            if command == "status":
                try:
                    response = sock.recv(1024)
                except socket.timeout:
                    pass

            sock.close()
            logger.info(f"Comando {command} enviado")
            return True, response

        except Exception as e:
            logger.error(f"Error en control: {e}")
            return False, None

    async def play(self) -> bool:
        """Reproducir"""
        success, _ = await self.send_control("play")
        return success

    async def pause(self) -> bool:
        """Pausar"""
        success, _ = await self.send_control("pause")
        return success

    async def get_status(self) -> Optional[dict]:
        """Obtener estado"""
        success, response = await self.send_control("status")
        if success and response:
            # TODO: Parsear respuesta
            return {"raw": response.hex()}
        return None

    async def delete_current(self) -> bool:
        """Eliminar archivo actual"""
        success, _ = await self.send_control("delete")
        return success

    async def is_online(self) -> bool:
        """Verificar si el ventilador está en línea"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.ip, self.UPLOAD_PORT))
            sock.close()
            return result == 0
        except:
            return False


# Uso de ejemplo
async def main():
    fan = FanProtocol("192.168.4.1")

    # Verificar conectividad
    if await fan.is_online():
        print("Ventilador en línea")

        # Subir archivo
        with open("animation.bin", "rb") as f:
            data = f.read()

        if await fan.upload_bin("animation.bin", data):
            print("Upload exitoso")

        # Reproducir
        await fan.play()
    else:
        print("Ventilador no disponible")


if __name__ == "__main__":
    asyncio.run(main())
