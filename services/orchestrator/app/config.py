"""
Configuración centralizada del sistema
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import yaml
from pathlib import Path


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Database
    database_url: str = Field(
        default="postgresql://holographic:holographic_secret@localhost:5432/holographic_avatar",
        env="DATABASE_URL"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # MinIO
    minio_endpoint: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin123", env="MINIO_SECRET_KEY")
    minio_bucket: str = "holographic-content"

    # AI Services URLs
    faster_liveportrait_url: str = Field(
        default="http://localhost:9871",
        env="FASTER_LIVEPORTRAIT_URL"
    )
    linly_tts_url: str = Field(default="http://localhost:8001", env="LINLY_TTS_URL")
    linly_llm_url: str = Field(default="http://localhost:8002", env="LINLY_LLM_URL")
    linly_avatar_url: str = Field(default="http://localhost:8003", env="LINLY_AVATAR_URL")
    linly_asr_url: str = Field(default="http://localhost:8004", env="LINLY_ASR_URL")

    # Frame Processing
    frame_processor_url: str = Field(
        default="http://localhost:8010",
        env="FRAME_PROCESSOR_URL"
    )
    polar_encoder_url: str = Field(
        default="http://localhost:8011",
        env="POLAR_ENCODER_URL"
    )
    fan_driver_url: str = Field(
        default="http://localhost:8012",
        env="FAN_DRIVER_URL"
    )

    # Default settings
    default_animation_duration: float = 5.0
    default_tts_voice: str = "es-MX-DaliaNeural"
    default_llm_model: str = "Qwen"

    class Config:
        env_file = ".env"
        case_sensitive = False


def load_yaml_config(path: str = "config/default.yaml") -> dict:
    """Carga configuración desde archivo YAML"""
    config_path = Path(path)
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


settings = Settings()
yaml_config = load_yaml_config()
