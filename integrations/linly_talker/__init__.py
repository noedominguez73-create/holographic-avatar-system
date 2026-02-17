"""
Wrapper para Linly-Talker
Integración con ASR, TTS, LLM y Avatar services
"""
from .asr_client import ASRClient
from .tts_client import TTSClient
from .llm_client import LLMClient
from .avatar_client import AvatarClient

__all__ = ['ASRClient', 'TTSClient', 'LLMClient', 'AvatarClient']
