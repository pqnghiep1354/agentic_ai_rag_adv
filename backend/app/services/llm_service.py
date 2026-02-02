"""
Ollama LLM service for text generation with streaming support
"""
import httpx
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
from ..core.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Service for interacting with Ollama API
    Supports streaming and non-streaming generation
    """

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: float = 300.0
    ):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate text using Ollama (non-streaming)

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stop: List of stop sequences
            **kwargs: Additional Ollama parameters

        Returns:
            Generated text
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": top_p,
                    **kwargs
                }
            }

            if system:
                payload["system"] = system

            if stop:
                payload["options"]["stop"] = stop

            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except httpx.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise Exception(f"Failed to generate text: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate text using Ollama with streaming

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stop: List of stop sequences
            **kwargs: Additional Ollama parameters

        Yields:
            Text chunks as they are generated
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": top_p,
                    **kwargs
                }
            }

            if system:
                payload["system"] = system

            if stop:
                payload["options"]["stop"] = stop

            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            import json
                            chunk = json.loads(line)

                            if chunk.get("response"):
                                yield chunk["response"]

                            # Check if generation is done
                            if chunk.get("done", False):
                                break

                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON line: {line}")
                            continue

        except httpx.HTTPError as e:
            logger.error(f"Ollama streaming HTTP error: {e}")
            raise Exception(f"Failed to stream text: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Chat completion using Ollama (non-streaming)

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stop: List of stop sequences
            **kwargs: Additional Ollama parameters

        Returns:
            Assistant response
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": top_p,
                    **kwargs
                }
            }

            if stop:
                payload["options"]["stop"] = stop

            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            message = result.get("message", {})
            return message.get("content", "")

        except httpx.HTTPError as e:
            logger.error(f"Ollama chat HTTP error: {e}")
            raise Exception(f"Failed to complete chat: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Chat completion using Ollama with streaming

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stop: List of stop sequences
            **kwargs: Additional Ollama parameters

        Yields:
            Text chunks as they are generated
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": top_p,
                    **kwargs
                }
            }

            if stop:
                payload["options"]["stop"] = stop

            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            import json
                            chunk = json.loads(line)

                            message = chunk.get("message", {})
                            if message.get("content"):
                                yield message["content"]

                            # Check if generation is done
                            if chunk.get("done", False):
                                break

                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON line: {line}")
                            continue

        except httpx.HTTPError as e:
            logger.error(f"Ollama chat streaming HTTP error: {e}")
            raise Exception(f"Failed to stream chat: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama chat streaming error: {e}")
            raise

    async def check_health(self) -> bool:
        """
        Check if Ollama service is available

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def pull_model(self, model: Optional[str] = None) -> bool:
        """
        Pull/download a model from Ollama

        Args:
            model: Model name (uses default if not specified)

        Returns:
            True if successful
        """
        model_name = model or self.model

        try:
            logger.info(f"Pulling Ollama model: {model_name}")

            response = await self.client.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": False},
                timeout=600.0  # 10 minutes for model download
            )
            response.raise_for_status()

            logger.info(f"Successfully pulled model: {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False


# Global singleton instance
_ollama_service: Optional[OllamaService] = None


def get_ollama_service() -> OllamaService:
    """
    Get global Ollama service instance

    Returns:
        OllamaService instance
    """
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
    return _ollama_service
