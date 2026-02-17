"""
Cliente para servicio LLM de Linly-Talker
"""
import aiohttp
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class LLMClient:
    """Cliente para Large Language Model"""

    # Modelos disponibles
    MODELS = {
        "qwen": "Qwen/Qwen-1_8B-Chat",
        "qwen2": "Qwen/Qwen1.5-0.5B-Chat",
        "chatglm": "THUDM/chatglm3-6b",
        "gemini": "gemini-pro",
        "gpt": "gpt-3.5-turbo",
    }

    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=60)

    async def generate(
        self,
        question: str,
        system_prompt: str = "",
        history: List[Dict[str, str]] = None,
        model: str = "qwen",
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> str:
        """
        Generar respuesta usando LLM.

        Args:
            question: Pregunta del usuario
            system_prompt: Instrucciones del sistema
            history: Historial de conversación [{role, content}]
            model: Modelo a usar
            max_tokens: Máximo de tokens en respuesta
            temperature: Creatividad (0-1)

        Returns:
            Respuesta generada
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/llm_response",
                    json={
                        "question": question,
                        "system_prompt": system_prompt,
                        "history": history or [],
                        "model": model,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "")
                    else:
                        error = await response.text()
                        logger.error(f"LLM error {response.status}: {error}")
                        return "Lo siento, no pude generar una respuesta."

        except aiohttp.ClientError as e:
            logger.error(f"LLM connection error: {e}")
            return "Lo siento, estoy teniendo problemas técnicos."

    async def generate_with_context(
        self,
        question: str,
        context: str,
        system_prompt: str = "",
        model: str = "qwen"
    ) -> str:
        """
        Generar respuesta con contexto adicional (RAG-style).

        Args:
            question: Pregunta del usuario
            context: Información contextual relevante
            system_prompt: Instrucciones del sistema
            model: Modelo a usar
        """
        enhanced_prompt = f"""
{system_prompt}

Información relevante:
{context}

Responde basándote en la información proporcionada.
"""
        return await self.generate(
            question=question,
            system_prompt=enhanced_prompt,
            model=model
        )

    async def change_model(
        self,
        model: str,
        api_key: Optional[str] = None
    ) -> bool:
        """Cambiar modelo LLM"""
        try:
            model_path = self.MODELS.get(model, model)

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/llm_change_model",
                    json={
                        "model": model_path,
                        "api_key": api_key
                    }
                ) as response:
                    return response.status == 200
        except:
            return False

    async def health_check(self) -> bool:
        """Verificar disponibilidad del servicio"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except:
            return False

    def get_system_prompt_for_mode(self, mode: str) -> str:
        """Obtener prompt del sistema según el modo"""
        prompts = {
            "receptionist": """Eres un recepcionista virtual profesional y amigable.
Tu trabajo es dar la bienvenida a los visitantes y responder preguntas básicas.
- Sé cordial y profesional
- Responde de forma concisa (2-3 oraciones)
- Si no sabes algo, sugiere hablar con personal humano
- Usa un tono cálido pero formal""",

            "menu": """Eres un mesero virtual experto en el menú del restaurante.
Tu trabajo es ayudar a los clientes a elegir platillos.
- Describe los platillos de forma apetitosa
- Sugiere maridajes y complementos
- Informa sobre ingredientes y alérgenos si preguntan
- Sé entusiasta pero no invasivo""",

            "catalog": """Eres un asistente de ventas virtual amigable.
Tu trabajo es ayudar a los clientes a encontrar productos.
- Conoce bien el catálogo de productos
- Sugiere opciones basadas en preferencias
- Informa sobre tallas, colores y disponibilidad
- Sé servicial sin ser insistente""",

            "memorial": """Eres un asistente empático y respetuoso.
Tu trabajo es ayudar a las personas a crear recuerdos especiales.
- Sé cálido y comprensivo
- Guía el proceso de forma clara
- Respeta la emotividad del momento
- Mantén un tono tranquilo y reconfortante"""
        }

        return prompts.get(mode, "Eres un asistente virtual útil y amigable.")
