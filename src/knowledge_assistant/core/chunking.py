"""Split long text into overlapping, sentence-aware chunks sized by token budget.

The original app embedded whole documents as one vector and silently truncated at the
model limit. Chunking is what makes long PDFs actually searchable.

Token counting uses a cheap approximation (~4 chars/token for English) so this module
has no model dependency; the embedder truncates safely if we're slightly over.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])|\n{2,}")


@dataclass(frozen=True)
class TextChunk:
    ord: int
    text: str
    token_count: int


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def split_sentences(text: str) -> list[str]:
    parts = _SENTENCE_RE.split(text)
    return [p.strip() for p in parts if p and p.strip()]


def chunk_text(text: str, max_tokens: int = 512, overlap_tokens: int = 64) -> list[TextChunk]:
    """Greedy sentence packing with overlap carried from the tail of the previous chunk."""
    if overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be smaller than max_tokens")
    text = text.strip()
    if not text:
        return []
    if estimate_tokens(text) <= max_tokens:
        return [TextChunk(0, text, estimate_tokens(text))]

    sentences = split_sentences(text)
    # a single sentence longer than the budget gets hard-split on whitespace
    units: list[str] = []
    for s in sentences:
        if estimate_tokens(s) <= max_tokens:
            units.append(s)
        else:
            words = s.split()
            step = max(1, max_tokens * 4 // 6)  # ~ words per chunk at 6 chars/word
            for i in range(0, len(words), step):
                units.append(" ".join(words[i : i + step]))

    chunks: list[TextChunk] = []
    current: list[str] = []
    current_tokens = 0
    for unit in units:
        ut = estimate_tokens(unit)
        if current and current_tokens + ut > max_tokens:
            body = " ".join(current)
            chunks.append(TextChunk(len(chunks), body, estimate_tokens(body)))
            # carry overlap: keep trailing sentences up to overlap budget
            carried: list[str] = []
            carried_tokens = 0
            for prev in reversed(current):
                pt = estimate_tokens(prev)
                if carried_tokens + pt > overlap_tokens:
                    break
                carried.insert(0, prev)
                carried_tokens += pt
            current = carried
            current_tokens = carried_tokens
        current.append(unit)
        current_tokens += ut
    if current:
        body = " ".join(current)
        chunks.append(TextChunk(len(chunks), body, estimate_tokens(body)))
    return chunks
