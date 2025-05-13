from __future__ import annotations

from ...config import Settings
from .base import LLMProvider, LLMUnavailable, NullProvider


def make_provider(settings: Settings) -> LLMProvider:
    """Build the configured provider; fall back to NullProvider rather than crash at startup."""
    from . import providers

    try:
        if settings.llm_provider == "ollama":
            return providers.OllamaProvider(settings.llm_model, settings.ollama_host)
        if settings.llm_provider == "openai":
            return providers.OpenAIProvider(settings.llm_model, settings.openai_api_key)
        if settings.llm_provider == "anthropic":
            return providers.AnthropicProvider(settings.llm_model, settings.anthropic_api_key)
    except LLMUnavailable:
        return NullProvider()
    return NullProvider()
