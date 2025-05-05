"""RAG question answering: retrieve chunks, ask the LLM with citations, stream the answer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from .llm import ChatMessage, LLMProvider
from .search import HybridSearch, SearchHit

SYSTEM = """You answer questions using ONLY the provided context from the user's knowledge base.
Cite sources inline as [n] where n is the context number. If the context does not contain
the answer, say so plainly and do not invent facts."""


@dataclass
class Answer:
    text: str
    sources: list[SearchHit]


def _context_block(hits: list[SearchHit]) -> str:
    return "\n\n".join(f"[{i + 1}] ({h.entry_title})\n{h.text}" for i, h in enumerate(hits))


def _messages(question: str, hits: list[SearchHit]) -> list[ChatMessage]:
    return [
        ChatMessage("system", SYSTEM),
        ChatMessage("user", f"Context:\n{_context_block(hits)}\n\nQuestion: {question}"),
    ]


class QAService:
    def __init__(self, search: HybridSearch, provider: LLMProvider, max_sources: int = 6):
        self.search = search
        self.provider = provider
        self.max_sources = max_sources

    def retrieve(self, question: str, category_id=None, topic_id=None) -> list[SearchHit]:
        return self.search.search(question, limit=self.max_sources, category_id=category_id, topic_id=topic_id)

    def answer(self, question: str, category_id=None, topic_id=None) -> Answer:
        hits = self.retrieve(question, category_id, topic_id)
        if not hits:
            return Answer("I couldn't find anything relevant in your knowledge base.", [])
        return Answer(self.provider.chat(_messages(question, hits)), hits)

    def stream_from_hits(self, question: str, hits: list[SearchHit]) -> Iterator[str]:
        return self.provider.stream(_messages(question, hits))

    def stream(self, question: str, category_id=None, topic_id=None) -> tuple[list[SearchHit], Iterator[str]]:
        hits = self.retrieve(question, category_id, topic_id)
        if not hits:
            return [], iter(["I couldn't find anything relevant in your knowledge base."])
        return hits, self.stream_from_hits(question, hits)
