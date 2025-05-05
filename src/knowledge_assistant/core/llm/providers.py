"""Concrete providers. SDKs are imported lazily so the base install stays light."""

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

