"""
Wrapper para led-hologram-propeller
Integración con el protocolo del ventilador holográfico
"""
from .encoder_wrapper import PolarEncoderWrapper
from .fan_protocol import FanProtocol

__all__ = ['PolarEncoderWrapper', 'FanProtocol']
