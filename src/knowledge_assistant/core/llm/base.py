"""Provider-agnostic chat interface. Plain chat + streaming only (no tool loop in v1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol


class LLMUnavailable(RuntimeError):
    """Provider not configured, not reachable, or missing its optional package."""


@dataclass(frozen=True)
class ChatMessage:
    role: str  # system | user | assistant
    content: str


class LLMProvider(Protocol):
    name: str
    model: str

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2, max_tokens: int = 1024) -> str: ...

    def stream(self, messages: list[ChatMessage], *, temperature: float = 0.2, max_tokens: int = 1024) -> Iterator[str]: ...

    def is_available(self) -> bool: ...


class NullProvider:
    """Used when no LLM is configured. Search still works; Q&A explains what's missing."""

    name = "none"
    model = ""

    def chat(self, messages, *, temperature=0.2, max_tokens=1024) -> str:
        raise LLMUnavailable("No LLM provider configured. Set KA_LLM_PROVIDER to ollama, openai or anthropic.")

    def stream(self, messages, *, temperature=0.2, max_tokens=1024):
        raise LLMUnavailable("No LLM provider configured. Set KA_LLM_PROVIDER to ollama, openai or anthropic.")

    def is_available(self) -> bool:
        return False


class FakeProvider:
    """Deterministic provider for tests: echoes a canned reply or the last user message."""

    name = "fake"
    model = "fake"

    def __init__(self, reply: str | None = None):
        self.reply = reply
        self.calls: list[list[ChatMessage]] = []

    def chat(self, messages, *, temperature=0.2, max_tokens=1024) -> str:
        self.calls.append(list(messages))
        return self.reply if self.reply is not None else f"echo: {messages[-1].content}"

    def stream(self, messages, *, temperature=0.2, max_tokens=1024):
        for word in self.chat(messages).split(" "):
            yield word + " "

    def is_available(self) -> bool:
        return True
