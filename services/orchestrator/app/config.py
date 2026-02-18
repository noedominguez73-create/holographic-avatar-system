"""
Configuración centralizada del sistema
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = Field(default=8000, alias="PORT")
    debug: bool = False

    # Database - Railway inyecta DATABASE_URL automáticamente
    database_url: str = Field(
        default="postgresql://localhost:5432/holographic_avatar",
        alias="DATABASE_URL"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    # MinIO
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = "holographic-content"

    # AI Services
    faster_liveportrait_url: str = Field(default="http://localhost:9871", alias="FASTER_LIVEPORTRAIT_URL")
    linly_tts_url: str = Field(default="http://localhost:8001", alias="LINLY_TTS_URL")
    linly_llm_url: str = Field(default="http://localhost:8002", alias="LINLY_LLM_URL")
    linly_avatar_url: str = Field(default="http://localhost:8003", alias="LINLY_AVATAR_URL")
    linly_asr_url: str = Field(default="http://localhost:8004", alias="LINLY_ASR_URL")

    # Processing Services
    frame_processor_url: str = Field(default="http://localhost:8010", alias="FRAME_PROCESSOR_URL")
    polar_encoder_url: str = Field(default="http://localhost:8011", alias="POLAR_ENCODER_URL")
    fan_driver_url: str = Field(default="http://localhost:8012", alias="FAN_DRIVER_URL")

    # Defaults
    default_animation_duration: float = 5.0
    default_tts_voice: str = "es-MX-DaliaNeural"
    default_llm_model: str = "Qwen"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
        "populate_by_name": True
    }


settings = Settings()
