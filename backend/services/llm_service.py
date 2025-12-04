"""
LLM service for interacting with Anthropic Claude and OpenAI GPT.
Provides unified interface with automatic fallback.
"""

from anthropic import Anthropic
from openai import OpenAI
from typing import Optional, List
import json
import logging

from config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Unified interface for LLM providers with fallback."""

    def __init__(self):
        """Initialize LLM clients."""
        self.anthropic_client = None
        self.openai_client = None

        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        self.default_provider = settings.DEFAULT_LLM_PROVIDER
        self.default_model = settings.DEFAULT_MODEL

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[str] = None,  # "json" for structured output
        provider: Optional[str] = None,
    ) -> str:
        """
        Generate completion with automatic fallback.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            response_format: "json" for JSON output
            provider: Force specific provider ("anthropic" or "openai")

        Returns:
            Generated text response
        """
        provider = provider or self.default_provider

        try:
            if provider == "anthropic" and self.anthropic_client:
                return await self._anthropic_completion(
                    prompt, system_prompt, temperature, max_tokens
                )
            elif provider == "openai" and self.openai_client:
                return await self._openai_completion(
                    prompt, system_prompt, temperature, max_tokens, response_format
                )
            else:
                raise ValueError(f"Provider {provider} not available or not configured")

        except Exception as e:
            logger.error(f"Primary LLM provider {provider} failed: {e}")

            # Try fallback provider
            fallback_provider = "openai" if provider == "anthropic" else "anthropic"
            logger.info(f"Trying fallback provider: {fallback_provider}")

            if fallback_provider == "anthropic" and self.anthropic_client:
                return await self._anthropic_completion(
                    prompt, system_prompt, temperature, max_tokens
                )
            elif fallback_provider == "openai" and self.openai_client:
                return await self._openai_completion(
                    prompt, system_prompt, temperature, max_tokens, response_format
                )
            else:
                raise Exception(f"Both LLM providers failed. Last error: {e}")

    async def _anthropic_completion(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate completion using Anthropic Claude."""
        logger.info("Using Anthropic Claude for completion")

        messages = [{"role": "user", "content": prompt}]

        response = self.anthropic_client.messages.create(
            model=self.default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=messages,
        )

        return response.content[0].text

    async def _openai_completion(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        response_format: Optional[str] = None,
    ) -> str:
        """Generate completion using OpenAI GPT."""
        logger.info("Using OpenAI GPT for completion")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": "gpt-4-turbo-preview",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = self.openai_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not configured. Required for embeddings.")

        logger.info("Generating embedding")

        response = self.openai_client.embeddings.create(
            model=settings.EMBEDDING_MODEL, input=text
        )

        return response.data[0].embedding

    async def parse_json_response(self, response: str) -> dict:
        """
        Parse JSON from LLM response, handling markdown code blocks.

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON dictionary
        """
        # Remove markdown code blocks if present
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        # Clean up and parse
        response = response.strip()
        return json.loads(response)
