"""
Router para información general de modos
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_modes():
    """Listar todos los modos disponibles"""
    return {
        "modes": [
            {
                "id": "memorial",
                "name": "Foto Memorial",
                "description": "Anima fotos de familiares para crear avatares holográficos",
                "enabled": True,
                "features": ["upload_photo", "generate_animation", "photo_booth"]
            },
            {
                "id": "receptionist",
                "name": "Recepcionista Virtual",
                "description": "Avatar que responde preguntas como recepcionista",
                "enabled": True,
                "features": ["voice_input", "llm_response", "tts_output", "avatar_animation"]
            },
            {
                "id": "menu",
                "name": "Menú Interactivo",
                "description": "Presenta el menú del restaurante de forma interactiva",
                "enabled": True,
                "features": ["categories", "items", "videos", "recommendations", "narration"]
            },
            {
                "id": "catalog",
                "name": "Catálogo de Tienda",
                "description": "Asistente virtual para tiendas de ropa y productos",
                "enabled": True,
                "features": ["search", "categories", "stock_check", "product_display"]
            },
            {
                "id": "videocall",
                "name": "Videollamada en Vivo",
                "description": "Transmite persona real al ventilador holográfico",
                "enabled": True,
                "features": ["webrtc", "realtime_streaming", "bidirectional_audio"]
            }
        ]
    }


@router.get("/{mode_id}")
async def get_mode_info(mode_id: str):
    """Obtener información detallada de un modo"""
    modes_info = {
        "memorial": {
            "id": "memorial",
            "name": "Foto Memorial",
            "description": "Sube una foto y genera un avatar animado holográfico",
            "endpoints": [
                {"method": "POST", "path": "/api/v1/memorial/upload-photo", "description": "Subir foto"},
                {"method": "GET", "path": "/api/v1/memorial/jobs/{job_id}", "description": "Estado de procesamiento"},
                {"method": "POST", "path": "/api/v1/memorial/play/{avatar_id}", "description": "Reproducir en ventilador"}
            ],
            "requirements": {
                "input": "Imagen JPEG/PNG con rostro visible",
                "processing_time": "~30 segundos",
                "output": "Video animado de 5 segundos"
            }
        },
        "receptionist": {
            "id": "receptionist",
            "name": "Recepcionista Virtual",
            "description": "Avatar conversacional que responde preguntas",
            "endpoints": [
                {"method": "POST", "path": "/api/v1/receptionist/start", "description": "Iniciar modo"},
                {"method": "POST", "path": "/api/v1/receptionist/conversation", "description": "Enviar mensaje"}
            ],
            "requirements": {
                "avatar": "Imagen de avatar predefinida",
                "llm": "Qwen/GPT configurado",
                "tts": "EdgeTTS o CosyVoice"
            }
        },
        "menu": {
            "id": "menu",
            "name": "Menú Interactivo",
            "description": "Presenta platillos del restaurante",
            "endpoints": [
                {"method": "GET", "path": "/api/v1/menu/categories", "description": "Listar categorías"},
                {"method": "GET", "path": "/api/v1/menu/items", "description": "Listar platillos"},
                {"method": "POST", "path": "/api/v1/menu/show-item/{id}", "description": "Mostrar en holograma"},
                {"method": "POST", "path": "/api/v1/menu/recommend", "description": "Obtener recomendaciones"}
            ]
        },
        "catalog": {
            "id": "catalog",
            "name": "Catálogo de Tienda",
            "description": "Asistente de ventas virtual",
            "endpoints": [
                {"method": "GET", "path": "/api/v1/catalog/products", "description": "Buscar productos"},
                {"method": "GET", "path": "/api/v1/catalog/products/{id}/availability", "description": "Ver stock"},
                {"method": "POST", "path": "/api/v1/catalog/show-product/{id}", "description": "Mostrar en holograma"}
            ]
        },
        "videocall": {
            "id": "videocall",
            "name": "Videollamada",
            "description": "Streaming de persona real al holograma",
            "endpoints": [
                {"method": "POST", "path": "/api/v1/videocall/start", "description": "Iniciar llamada WebRTC"},
                {"method": "POST", "path": "/api/v1/videocall/{session_id}/ice", "description": "Agregar ICE candidate"},
                {"method": "POST", "path": "/api/v1/videocall/{session_id}/end", "description": "Terminar llamada"}
            ],
            "requirements": {
                "protocol": "WebRTC",
                "max_fps": 15,
                "audio": "Bidireccional"
            }
        }
    }

    if mode_id not in modes_info:
        return {"error": "Modo no encontrado"}

    return modes_info[mode_id]
