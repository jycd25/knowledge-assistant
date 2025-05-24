"""Concrete providers. Each imports its SDK lazily so the base install stays light."""

from __future__ import annotations

from typing import Iterator

from .base import ChatMessage, LLMUnavailable


def _dicts(messages: list[ChatMessage]) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in messages]


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str = "llama3.2", host: str = "http://127.0.0.1:11434"):
        try:
            import ollama
        except ImportError as e:
            raise LLMUnavailable("pip install 'knowledge-assistant[ollama]'") from e
        self.model = model
        self._client = ollama.Client(host=host)

    def chat(self, messages, *, temperature=0.2, max_tokens=1024) -> str:
        r = self._client.chat(model=self.model, messages=_dicts(messages),
                              options={"temperature": temperature, "num_predict": max_tokens})
        return r["message"]["content"]

    def stream(self, messages, *, temperature=0.2, max_tokens=1024) -> Iterator[str]:
        for part in self._client.chat(model=self.model, messages=_dicts(messages), stream=True,
                                      options={"temperature": temperature, "num_predict": max_tokens}):
            yield part["message"]["content"]

    def is_available(self) -> bool:
        try:
            self._client.list()
            return True
        except Exception:
            return False


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMUnavailable("pip install 'knowledge-assistant[openai]'") from e
        if not api_key:
            raise LLMUnavailable("KA_OPENAI_API_KEY is not set")
        self.model = model
        self._client = OpenAI(api_key=api_key)

    def chat(self, messages, *, temperature=0.2, max_tokens=1024) -> str:
        r = self._client.chat.completions.create(model=self.model, messages=_dicts(messages),
                                                 temperature=temperature, max_tokens=max_tokens)
        return r.choices[0].message.content or ""

    def stream(self, messages, *, temperature=0.2, max_tokens=1024) -> Iterator[str]:
        for chunk in self._client.chat.completions.create(model=self.model, messages=_dicts(messages),
                                                          temperature=temperature, max_tokens=max_tokens, stream=True):
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    def is_available(self) -> bool:
        return True


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str = "claude-3-5-haiku-latest", api_key: str | None = None):
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise LLMUnavailable("pip install 'knowledge-assistant[anthropic]'") from e
        if not api_key:
            raise LLMUnavailable("KA_ANTHROPIC_API_KEY is not set")
        self.model = model
        self._client = Anthropic(api_key=api_key)

    @staticmethod
    def _split(messages: list[ChatMessage]) -> tuple[str, list[dict]]:
        system = "\n".join(m.content for m in messages if m.role == "system")
        rest = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        return system, rest

    def chat(self, messages, *, temperature=0.2, max_tokens=1024) -> str:
        system, rest = self._split(messages)
        r = self._client.messages.create(model=self.model, system=system or None, messages=rest,
                                         temperature=temperature, max_tokens=max_tokens)
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")

    def stream(self, messages, *, temperature=0.2, max_tokens=1024) -> Iterator[str]:
        system, rest = self._split(messages)
        with self._client.messages.stream(model=self.model, system=system or None, messages=rest,
                                          temperature=temperature, max_tokens=max_tokens) as s:
            yield from s.text_stream

    def is_available(self) -> bool:
        return True
