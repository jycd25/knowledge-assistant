"""Note processing: turn raw text into a structured markdown note.

Two paths, as in the original:
- heuristic (no LLM): title from the first sentence, sections split on discourse markers,
  frequency-based tags, first-sentence summary.
- LLM: a structured prompt combining formatting rules, user preferences and the user's
  request. Falls back to heuristic if the provider is unavailable.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .chunking import split_sentences
from .llm import ChatMessage, LLMProvider, LLMUnavailable

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he", "in", "is", "it",
    "its", "of", "on", "that", "the", "to", "was", "were", "will", "with", "this", "these", "those",
}
SECTION_MARKERS = ("additionally", "moreover", "furthermore", "however", "on the other hand", "in contrast")
INTRO_PHRASES = ("today i learned", "i learned", "note about", "today's note")

FORMAT_RULES = """Format Requirements:
1. Use markdown formatting
2. Create clear section headers (H1, H2)
3. Use bullet points for lists
4. Include a summary section
5. Add relevant tags at the end

Required Sections:
- Title (H1)
- Summary
- Main Points
- Action Items (if applicable)
- Tags"""


@dataclass
class ProcessedNote:
    title: str
    markdown: str
    tags: list[str] = field(default_factory=list)
    used_llm: bool = False
    applied_preferences: list[dict] = field(default_factory=list)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def extract_title(text: str) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return "Untitled Note"
    first = sentences[0].lower()
    for phrase in INTRO_PHRASES:
        first = first.replace(phrase, "")
    words = [w for w in _words(first) if w not in STOP_WORDS][:6]
    return " ".join(words).title() or "Untitled Note"


def extract_tags(text: str, n: int = 5) -> list[str]:
    words = [w for w in _words(text) if w not in STOP_WORDS and len(w) > 3]
    return [f"#{w.title()}" for w, _ in Counter(words).most_common(n)]


def identify_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: list[str] = []
    topic = "Main Points"
    for sentence in split_sentences(text):
        if any(m in sentence.lower() for m in SECTION_MARKERS) and current:
            sections[topic] = " ".join(current)
            current = []
            topic = " ".join([w for w in _words(sentence) if w not in STOP_WORDS][:3]).title() or "More"
        current.append(sentence)
    if current:
        sections[topic] = " ".join(current)
    return sections


def process_heuristic(text: str) -> ProcessedNote:
    title = extract_title(text)
    sections = identify_sections(text)
    tags = extract_tags(text)
    lines = [f"# {title}", ""]
    for name, body in sections.items():
        lines += [f"## {name}", body, ""]
    if len(text.split()) >= 50:
        summary = " ".join(split_sentences(b)[0] for b in sections.values() if split_sentences(b))
        lines += ["## Summary", summary, ""]
    if tags:
        lines += ["## Tags", " ".join(tags)]
    return ProcessedNote(title=title, markdown="\n".join(lines).strip(), tags=tags)


def build_prompt(text: str, user_request: str | None, preferences: list[dict]) -> str:
    parts = ["=== FORMATTING INSTRUCTIONS ===", FORMAT_RULES]
    if preferences:
        parts.append("=== USER PREFERENCES ===")
        for p in preferences:
            if p["key"].lower() == "special emphasis":
                parts.append("IMPORTANT: surround names of important figures and key terms with "
                             "double asterisks for bold. Example: **Albert Einstein**")
            else:
                parts.append(f"{p['key']}: {p['value']}")
    if user_request:
        parts += ["=== USER REQUEST ===", user_request]
    parts += ["=== INPUT TEXT ===", text]
    return "\n\n".join(parts)


def process_with_llm(text: str, provider: LLMProvider, user_request: str | None = None,
                     preferences: list[dict] | None = None) -> ProcessedNote:
    prefs = preferences or []
    prompt = build_prompt(text, user_request, prefs)
    system = "You are a helpful note processing assistant that follows formatting instructions precisely."
    try:
        out = provider.chat([ChatMessage("system", system), ChatMessage("user", prompt)],
                            temperature=0.7, max_tokens=2000)
    except LLMUnavailable:
        return process_heuristic(text)
    m = re.search(r"^#\s+(.+)$", out, re.M)
    title = m.group(1).strip() if m else extract_title(text)
    tags = re.findall(r"#[A-Za-z][\w-]+", out.split("## Tags")[-1]) if "## Tags" in out else extract_tags(text)
    return ProcessedNote(title=title, markdown=out.strip(), tags=tags, used_llm=True, applied_preferences=prefs)
