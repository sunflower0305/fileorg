"""LLM client for AI analysis."""

from typing import Optional, AsyncGenerator

import httpx
from openai import AsyncOpenAI
from loguru import logger

from ..config.settings import settings


class LLMClient:
    """OpenAI-compatible LLM client supporting DashScope, DeepSeek, etc."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
    ):
        self.base_url = base_url or settings.llm.base_url
        self.api_key = api_key or settings.llm.api_key
        self.model = model or settings.llm.model
        self.timeout = timeout or settings.llm.timeout
        self.temperature = temperature or settings.llm.temperature

        self._client: Optional[AsyncOpenAI] = None
        self._httpx_client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client."""
        if self._client is None:
            self._httpx_client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout=self.timeout, connect=5.0)
            )
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                http_client=self._httpx_client,
            )
        return self._client

    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Send a chat request and return the full response.

        Args:
            message: The user message.
            system_prompt: Optional system prompt.
            **kwargs: Additional arguments for the API call.

        Returns:
            The assistant's response content.
        """
        client = self._get_client()
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise

    async def chat_stream(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Send a chat request and stream the response.

        Args:
            message: The user message.
            system_prompt: Optional system prompt.
            **kwargs: Additional arguments for the API call.

        Yields:
            Chunks of the response content.
        """
        client = self._get_client()
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                stream=True,
                **kwargs,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM streaming request failed: {e}")
            raise

    async def close(self) -> None:
        """Close the client connection."""
        if self._httpx_client:
            await self._httpx_client.aclose()
            self._client = None
            self._httpx_client = None


# Global client instance
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
