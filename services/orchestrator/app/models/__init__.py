"""
Modelos Pydantic para el sistema
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class ModeType(str, Enum):
    MEMORIAL = "memorial"
    RECEPTIONIST = "receptionist"
    MENU = "menu"
    CATALOG = "catalog"
    VIDEOCALL = "videocall"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    BUSY = "busy"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


# ============================================
# SESIONES
# ============================================
class SessionCreate(BaseModel):
    device_id: UUID
    mode: ModeType
    avatar_id: Optional[UUID] = None
    config: Optional[Dict[str, Any]] = {}


class Session(BaseModel):
    id: UUID
    device_id: UUID
    mode: ModeType
    avatar_id: Optional[UUID]
    status: SessionStatus
    started_at: datetime
    ended_at: Optional[datetime]
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


# ============================================
# DISPOSITIVOS
# ============================================
class DeviceCreate(BaseModel):
    location_id: UUID
    name: str
    ip_address: str
    device_type: str = "led_fan_224"
    protocol_type: str = "tcp"
    tcp_port: int = 5499
    http_port: int = 80


class Device(BaseModel):
    id: UUID
    location_id: UUID
    name: str
    ip_address: str
    device_type: str
    protocol_type: str
    status: DeviceStatus
    last_heartbeat: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================
# AVATARES
# ============================================
class AvatarCreate(BaseModel):
    name: str
    description: Optional[str] = None
    avatar_type: str = "custom"
    animation_preset: str = "natural"


class Avatar(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    image_url: str
    thumbnail_url: Optional[str]
    avatar_type: str
    is_active: bool

    class Config:
        from_attributes = True


# ============================================
# MODO MEMORIAL
# ============================================
class MemorialUploadResponse(BaseModel):
    job_id: str
    avatar_id: UUID
    status: str = "processing"
    estimated_seconds: int = 30


class MemorialPlayRequest(BaseModel):
    device_id: UUID
    animation_preset: str = "natural"
    loop: bool = True
    duration_seconds: float = 5.0


# ============================================
# MODO RECEPCIONISTA
# ============================================
class ReceptionistStartRequest(BaseModel):
    device_id: UUID
    avatar_id: UUID
    greeting_message: Optional[str] = "¡Hola! ¿En qué puedo ayudarte?"
    system_prompt: Optional[str] = None


class ConversationInput(BaseModel):
    session_id: UUID
    audio_base64: Optional[str] = None
    text: Optional[str] = None


class ConversationResponse(BaseModel):
    response_text: str
    audio_url: Optional[str]
    video_url: Optional[str]
    intent: Optional[str]
    entities: Optional[Dict[str, Any]]


# ============================================
# MODO MENÚ
# ============================================
class MenuCategory(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    image_url: Optional[str]
    items_count: int = 0

    class Config:
        from_attributes = True


class MenuItem(BaseModel):
    id: UUID
    category_id: UUID
    name: str
    description: Optional[str]
    price: float
    currency: str = "MXN"
    image_url: Optional[str]
    video_url: Optional[str]
    ingredients: Optional[List[str]]
    is_available: bool
    is_featured: bool

    class Config:
        from_attributes = True


class MenuRecommendRequest(BaseModel):
    session_id: UUID
    preferences: List[str] = []
    dietary_restrictions: List[str] = []
    budget_max: Optional[float] = None


class ShowItemRequest(BaseModel):
    device_id: UUID
    show_video: bool = False
    narrate: bool = True


# ============================================
# MODO CATÁLOGO
# ============================================
class CatalogCategory(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    image_url: Optional[str]
    parent_id: Optional[UUID]

    class Config:
        from_attributes = True


class Product(BaseModel):
    id: UUID
    category_id: UUID
    sku: Optional[str]
    name: str
    description: Optional[str]
    price: float
    currency: str = "MXN"
    images: List[str] = []
    sizes: List[str] = []
    colors: List[str] = []
    is_available: bool

    class Config:
        from_attributes = True


class ProductAvailability(BaseModel):
    product_id: UUID
    location_id: UUID
    size: Optional[str]
    color: Optional[str]
    quantity: int
    is_available: bool


class ShowProductRequest(BaseModel):
    device_id: UUID
    image_index: int = 0
    rotate: bool = False


# ============================================
# MODO VIDEOLLAMADA
# ============================================
class VideocallStartRequest(BaseModel):
    device_id: UUID
    caller_id: str
    webrtc_offer: str


class VideocallStartResponse(BaseModel):
    session_id: UUID
    webrtc_answer: str
    ice_candidates: List[Dict[str, Any]]


class ICECandidate(BaseModel):
    candidate: str
    sdpMid: str
    sdpMLineIndex: int


# ============================================
# UBICACIONES
# ============================================
class LocationCreate(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    timezone: str = "America/Mexico_City"


class Location(BaseModel):
    id: UUID
    name: str
    address: Optional[str]
    city: Optional[str]
    is_active: bool
    devices_count: int = 0

    class Config:
        from_attributes = True
