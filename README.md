# Sistema de Avatar Holográfico para Ventilador LED

Sistema modular para crear experiencias de avatar holográfico con ventiladores LED 3D.

## Modos de Operación

| Modo | Descripción | Uso |
|------|-------------|-----|
| **Memorial** | Anima fotos de familiares | Photo booth con hologramas |
| **Recepcionista** | Avatar que responde preguntas | Entrada de restaurante/hotel |
| **Menú Interactivo** | Presenta platillos con videos | Restaurantes |
| **Catálogo** | Muestra productos y stock | Tiendas de ropa |
| **Videollamada** | Persona real en holograma | Comunicación remota |

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│              ORCHESTRATOR (FastAPI :8000)               │
│  Memorial │ Recepción │ Menú │ Catálogo │ Videocall    │
└─────────────────────────────────────────────────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───┴───┐           ┌─────┴─────┐         ┌─────┴─────┐
│  AI   │           │  Frame    │         │   Fan     │
│ Svcs  │           │ Processor │         │  Driver   │
└───────┘           └───────────┘         └───────────┘
```

## Requisitos

- Python 3.10+
- Docker y Docker Compose
- GPU NVIDIA con CUDA 12+ (para AI)
- Ventilador holográfico LED con WiFi

## Instalación Rápida

```bash
# 1. Clonar/navegar al proyecto
cd "C:\avatar ventilador\holographic-system"

# 2. Iniciar servicios base
docker-compose up -d postgres redis minio

# 3. Instalar dependencias del orchestrator
cd services/orchestrator
pip install -r requirements.txt

# 4. Iniciar orchestrator
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Configuración

### Variables de Entorno

```env
DATABASE_URL=postgresql://holographic:holographic_secret@localhost:5432/holographic_avatar
REDIS_URL=redis://localhost:6379
MINIO_ENDPOINT=localhost:9000

# AI Services (Linly-Talker)
LINLY_TTS_URL=http://localhost:8001
LINLY_LLM_URL=http://localhost:8002
LINLY_AVATAR_URL=http://localhost:8003

# FasterLivePortrait
FASTER_LIVEPORTRAIT_URL=http://localhost:9871
```

### Configurar Ventilador

1. Conectar el ventilador a la red WiFi
2. Registrar dispositivo:

```bash
curl -X POST "http://localhost:8000/api/v1/devices" \
  -H "Content-Type: application/json" \
  -d '{"ip_address": "192.168.4.1", "name": "Fan-1", "location_id": "..."}'
```

## Uso por Modo

### Modo 1: Memorial

```bash
# Subir foto
curl -X POST "http://localhost:8000/api/v1/memorial/upload-photo" \
  -F "photo=@familiar.jpg" \
  -F "user_email=user@email.com"

# Verificar estado
curl "http://localhost:8000/api/v1/memorial/jobs/{job_id}"

# Reproducir en ventilador
curl -X POST "http://localhost:8000/api/v1/memorial/play/{avatar_id}" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "...", "loop": true}'
```

### Modo 2: Recepcionista

```bash
# Iniciar modo
curl -X POST "http://localhost:8000/api/v1/receptionist/start" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "...",
    "avatar_id": "...",
    "greeting_message": "¡Bienvenido! ¿En qué puedo ayudarte?"
  }'

# Enviar mensaje
curl -X POST "http://localhost:8000/api/v1/receptionist/conversation" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "text": "¿Dónde está el baño?"}'
```

### Modo 3: Menú Interactivo

```bash
# Listar categorías
curl "http://localhost:8000/api/v1/menu/categories?location_id=..."

# Mostrar platillo
curl -X POST "http://localhost:8000/api/v1/menu/show-item/{item_id}" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "...", "show_video": true, "narrate": true}'
```

### Modo 4: Catálogo

```bash
# Buscar productos
curl "http://localhost:8000/api/v1/catalog/products?query=vestido&location_id=..."

# Verificar stock
curl "http://localhost:8000/api/v1/catalog/products/{id}/availability?location_id=...&size=M"
```

### Modo 5: Videollamada

```bash
# Iniciar (enviar oferta SDP)
curl -X POST "http://localhost:8000/api/v1/videocall/start" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "...", "caller_id": "user1", "webrtc_offer": "..."}'
```

## Servicios AI Requeridos

El sistema utiliza los siguientes repositorios (deben estar corriendo):

| Servicio | Puerto | Repositorio |
|----------|--------|-------------|
| FasterLivePortrait | 9871 | `FasterLivePortrait/` |
| Linly-Talker TTS | 8001 | `Linly-Talker/api/tts_api.py` |
| Linly-Talker LLM | 8002 | `Linly-Talker/api/llm_api.py` |
| Linly-Talker Avatar | 8003 | `Linly-Talker/api/talker_api.py` |

### Iniciar Linly-Talker

```bash
cd "C:\avatar ventilador\Linly-Talker"

# TTS
fastapi dev api/tts_api.py --host 0.0.0.0 --port 8001

# LLM
fastapi dev api/llm_api.py --host 0.0.0.0 --port 8002

# Avatar
fastapi dev api/talker_api.py --host 0.0.0.0 --port 8003
```

### Iniciar FasterLivePortrait

```bash
cd "C:\avatar ventilador\FasterLivePortrait"
python api.py
```

## API Documentation

Una vez iniciado el orchestrator, la documentación está disponible en:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Protocolo del Ventilador

El sistema soporta dos protocolos:

### TCP (Puerto 5499)
- Upload de archivos `.bin` completos
- Control via puerto 5233 (play/pause/status)
- Delay mínimo: 30ms entre paquetes

### HTTP (si el modelo lo soporta)
- Streaming frame-a-frame
- Endpoint: `POST /upload_frame`

## Estructura del Proyecto

```
holographic-system/
├── services/
│   ├── orchestrator/     # API principal
│   ├── frame-processor/  # Procesamiento de frames
│   ├── polar-encoder/    # Conversión a formato ventilador
│   └── fan-driver/       # Comunicación con hardware
├── integrations/
│   ├── faster_live_portrait/
│   ├── linly_talker/
│   └── led_hologram/
├── database/
├── config/
└── docker-compose.yml
```

## Notas Importantes

- **Fondo negro puro**: Usar RGB(0,0,0) para efecto holográfico
- **FPS del ventilador**: ~10 FPS máximo
- **Resolución**: 224 LEDs de diámetro típico
- **GPU recomendada**: NVIDIA con 8GB+ VRAM

## Licencia

MIT
