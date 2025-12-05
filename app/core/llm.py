"""LLM provider abstractions and utilities."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import google.generativeai as genai
import anthropic
from pydantic import BaseModel

from .config import settings


class Provider(str, Enum):
    """LLM providers."""
    GEMINI = "gemini"
    CLAUDE = "claude"


class LLMConfig(BaseModel):
    """Configuration for LLM calls."""
    provider: Provider
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None


class LLMResponse(BaseModel):
    """Response from LLM call."""
    content: str
    usage: Dict[str, Any]
    finish_reason: str


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, config: LLMConfig) -> LLMResponse:
        """Generate text from prompt."""
        pass

    @abstractmethod
    async def generate_with_tools(self, prompt: str, tools: List[Dict], config: LLMConfig) -> LLMResponse:
        """Generate text with tool calling support."""
        pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider."""

    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        self.client = genai

    async def generate(self, prompt: str, config: LLMConfig) -> LLMResponse:
        """Generate text using Gemini."""
        model = self.client.GenerativeModel(config.model)

        generation_config = genai.types.GenerationConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
            top_p=config.top_p,
            top_k=config.top_k,
        )

        response = await model.generate_content_async(
            prompt,
            generation_config=generation_config,
        )

        return LLMResponse(
            content=response.text,
            usage={"candidates": len(response.candidates) if response.candidates else 0},
            finish_reason=response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN",
        )

    async def generate_with_tools(self, prompt: str, tools: List[Dict], config: LLMConfig) -> LLMResponse:
        """Generate with tools - simplified for now."""
        # For now, just call regular generate
        # TODO: Implement proper tool calling for Gemini
        return await self.generate(prompt, config)


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate(self, prompt: str, config: LLMConfig) -> LLMResponse:
        """Generate text using Claude."""
        message = await self.client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens or 4096,
            temperature=config.temperature,
            system=prompt,
            messages=[],
        )

        return LLMResponse(
            content=message.content[0].text if message.content else "",
            usage=message.usage.model_dump() if message.usage else {},
            finish_reason=message.stop_reason or "UNKNOWN",
        )

    async def generate_with_tools(self, prompt: str, tools: List[Dict], config: LLMConfig) -> LLMResponse:
        """Generate with tools using Claude."""
        # Convert tools to Claude format
        claude_tools = []
        for tool in tools:
            claude_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"]
            })

        message = await self.client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens or 4096,
            temperature=config.temperature,
            system=prompt,
            messages=[],
            tools=claude_tools,
        )

        return LLMResponse(
            content=message.content[0].text if message.content else "",
            usage=message.usage.model_dump() if message.usage else {},
            finish_reason=message.stop_reason or "UNKNOWN",
        )


class LLMManager:
    """Manager for LLM providers."""

    def __init__(self):
        self.providers = {
            Provider.GEMINI: GeminiProvider(),
            Provider.CLAUDE: ClaudeProvider(),
        }

    async def generate(
        self,
        prompt: str,
        provider: Provider = Provider.GEMINI,
        model: str = "gemini-1.5-flash",
        **kwargs
    ) -> LLMResponse:
        """Generate text using specified provider."""
        config = LLMConfig(provider=provider, model=model, **kwargs)
        provider_instance = self.providers[provider]
        return await provider_instance.generate(prompt, config)

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict],
        provider: Provider = Provider.CLAUDE,
        model: str = "claude-3-sonnet-20240229",
        **kwargs
    ) -> LLMResponse:
        """Generate text with tools using specified provider."""
        config = LLMConfig(provider=provider, model=model, **kwargs)
        provider_instance = self.providers[provider]
        return await provider_instance.generate_with_tools(prompt, tools, config)


# Global LLM manager instance
llm_manager = LLMManager()
