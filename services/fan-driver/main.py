"""
Fan Driver Service
Comunicación con ventiladores holográficos LED via TCP y HTTP
Basado en led-hologram-propeller protocol
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
import asyncio
import socket
import struct
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

app = FastAPI(title="Fan Driver Service", version="1.0.0")
logger = logging.getLogger(__name__)

# Protocolo TCP del ventilador
TCP_CONTROL_PORT = 5233
TCP_UPLOAD_PORT = 5499
DEFAULT_FAN_IP = "192.168.4.1"

# Constantes del protocolo
PACKET_SIZE = 1460
PACKET_HEADER = bytes.fromhex("d3e0c9ba02014dd8")
PACKET_TYPE_NAME = b"0AgQ"
PACKET_TYPE_DATA = b"1GnH"
PACKET_TYPE_END = b"1AfF"
PACKET_TRAILER = bytes.fromhex("bfb5d2a2")

# Control commands
CONTROL_HEADER = bytes.fromhex("c0eeb7c9baa3020000000014cc")
CONTROL_TRAILER = bytes.fromhex("bfb5d2a2")


class FanStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    PLAYING = "playing"
    UPLOADING = "uploading"
    ERROR = "error"


@dataclass
class FanDevice:
    ip: str
    tcp_port: int = TCP_UPLOAD_PORT
    control_port: int = TCP_CONTROL_PORT
    status: FanStatus = FanStatus.OFFLINE
    current_file: Optional[str] = None


# Registro de dispositivos
devices: Dict[str, FanDevice] = {}


class TCPFanClient:
    """Cliente TCP para comunicación con ventilador"""

    def __init__(self, ip: str, port: int = TCP_UPLOAD_PORT):
        self.ip = ip
        self.port = port
        self.socket: Optional[socket.socket] = None

    async def connect(self) -> bool:
        """Conectar al ventilador"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.ip, self.port))
            logger.info(f"Conectado a ventilador {self.ip}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Error conectando a {self.ip}:{self.port}: {e}")
            return False

    def disconnect(self):
        """Desconectar"""
        if self.socket:
            self.socket.close()
            self.socket = None

    async def upload_file(self, filename: str, data: bytes, delay: float = 0.03) -> bool:
        """
        Subir archivo .bin al ventilador.

        Args:
            filename: Nombre del archivo (max 99 caracteres)
            data: Datos del archivo
            delay: Delay entre paquetes (mínimo 0.03s)

        Returns:
            True si exitoso
        """
        if not self.socket:
            if not await self.connect():
                return False

        try:
            # Preparar nombre (max 99 bytes)
            filename_bytes = filename.encode()[:99]

            # Paquete 1: Nombre del archivo
            file_size = len(data)
            name_packet = (
                PACKET_HEADER +
                PACKET_TYPE_NAME +
                struct.pack(">I", file_size) +
                filename_bytes +
                PACKET_TRAILER
            )

            self.socket.send(name_packet)
            await asyncio.sleep(delay)

            # Paquetes de datos
            data_payload_size = PACKET_SIZE - len(PACKET_HEADER) - len(PACKET_TYPE_DATA) - len(PACKET_TRAILER)

            offset = 0
            while offset < len(data):
                chunk = data[offset:offset + data_payload_size]

                # Pad si es necesario
                if len(chunk) < data_payload_size:
                    chunk += b'\x00' * (data_payload_size - len(chunk))

                data_packet = PACKET_HEADER + PACKET_TYPE_DATA + chunk + PACKET_TRAILER
                self.socket.send(data_packet)
                await asyncio.sleep(delay)

                offset += data_payload_size

            # Paquete final
            end_packet = PACKET_HEADER + PACKET_TYPE_END + PACKET_TRAILER
            self.socket.send(end_packet)

            logger.info(f"Archivo {filename} subido exitosamente ({file_size} bytes)")
            return True

        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            return False

    async def send_command(self, command: str) -> bool:
        """
        Enviar comando de control.

        Commands: play, pause, status, delete
        """
        commands = {
            "pause": b"34",
            "play": b"35",
            "status": b"38",
        }

        if command not in commands:
            logger.error(f"Comando desconocido: {command}")
            return False

        try:
            control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            control_socket.settimeout(5)
            control_socket.connect((self.ip, TCP_CONTROL_PORT))

            cmd_packet = (
                CONTROL_HEADER +
                commands[command] +
                b"lfhbfb5d2a2"
            )

            control_socket.send(cmd_packet)
            control_socket.close()

            logger.info(f"Comando {command} enviado a {self.ip}")
            return True

        except Exception as e:
            logger.error(f"Error enviando comando: {e}")
            return False


class HTTPFanClient:
    """Cliente HTTP para ventiladores que soportan API REST"""

    def __init__(self, ip: str, port: int = 80):
        self.base_url = f"http://{ip}:{port}"

    async def send_frame(self, frame_data: bytes) -> bool:
        """Enviar frame individual via HTTP"""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field('frame', frame_data, filename='frame.png')

                async with session.post(
                    f"{self.base_url}/upload_frame",
                    data=form,
                    timeout=aiohttp.ClientTimeout(total=1)
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"HTTP send error: {e}")
            return False

    async def stream_frames(self, frames: list, fps: int = 10) -> int:
        """Hacer streaming de múltiples frames"""
        delay = 1.0 / fps
        sent = 0

        for frame in frames:
            if await self.send_frame(frame):
                sent += 1
            await asyncio.sleep(delay)

        return sent


# Endpoints API

@app.post("/register")
async def register_device(
    ip: str,
    name: str = "Fan",
    protocol: str = "tcp"
):
    """Registrar un nuevo dispositivo"""
    device = FanDevice(
        ip=ip,
        tcp_port=TCP_UPLOAD_PORT if protocol == "tcp" else 80,
        status=FanStatus.OFFLINE
    )

    # Verificar conectividad
    if protocol == "tcp":
        client = TCPFanClient(ip)
        if await client.connect():
            device.status = FanStatus.ONLINE
            client.disconnect()
    else:
        # TODO: verificar HTTP
        pass

    devices[ip] = device

    return {
        "ip": ip,
        "name": name,
        "status": device.status.value,
        "protocol": protocol
    }


@app.get("/devices")
async def list_devices():
    """Listar dispositivos registrados"""
    return {
        ip: {
            "ip": dev.ip,
            "status": dev.status.value,
            "current_file": dev.current_file
        }
        for ip, dev in devices.items()
    }


@app.post("/upload/{device_ip}")
async def upload_to_device(
    device_ip: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Subir archivo .bin a un dispositivo"""
    if device_ip not in devices:
        # Registrar automáticamente
        devices[device_ip] = FanDevice(ip=device_ip)

    device = devices[device_ip]
    device.status = FanStatus.UPLOADING

    data = await file.read()
    filename = file.filename or "animation.bin"

    # Subir en background
    async def do_upload():
        client = TCPFanClient(device_ip)
        success = await client.upload_file(filename, data)
        client.disconnect()

        if success:
            device.status = FanStatus.PLAYING
            device.current_file = filename
        else:
            device.status = FanStatus.ERROR

    if background_tasks:
        background_tasks.add_task(do_upload)
        return {"status": "uploading", "device": device_ip, "filename": filename}
    else:
        await do_upload()
        return {"status": device.status.value, "device": device_ip}


@app.post("/control/{device_ip}/{command}")
async def control_device(device_ip: str, command: str):
    """Enviar comando de control (play, pause, status)"""
    client = TCPFanClient(device_ip)
    success = await client.send_command(command)

    return {
        "device": device_ip,
        "command": command,
        "success": success
    }


@app.post("/stream/{device_ip}")
async def stream_frame(
    device_ip: str,
    frame: UploadFile = File(...)
):
    """Enviar un frame individual (HTTP streaming)"""
    client = HTTPFanClient(device_ip)
    frame_data = await frame.read()
    success = await client.send_frame(frame_data)

    return {
        "device": device_ip,
        "success": success,
        "frame_size": len(frame_data)
    }


@app.get("/ping/{device_ip}")
async def ping_device(device_ip: str):
    """Verificar conectividad con dispositivo"""
    client = TCPFanClient(device_ip)
    online = await client.connect()
    client.disconnect()

    if device_ip in devices:
        devices[device_ip].status = FanStatus.ONLINE if online else FanStatus.OFFLINE

    return {
        "device": device_ip,
        "online": online
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
