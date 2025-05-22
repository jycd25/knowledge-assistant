"""Natural-language preference management via a two-step prompt chain:
classify the request (add / update / remove / list / help), then act.

Preferences are stored in the `preferences` table and injected into note-processing
prompts. Low-confidence results are returned as suggestions, never auto-saved.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .llm import ChatMessage, LLMProvider, LLMUnavailable
from .repositories import PreferenceRepository

HELP_TEXT = (
    "You can manage preferences in plain language:\n"
    "1. Add: 'Add a preference to use bullet points'\n"
    "2. Update: 'Change my formal style to casual'\n"
    "3. Remove: 'Remove my bullet points preference'\n"
    "4. List: 'Show me my preferences'"
)

CLASSIFY_PROMPT = """Classify this request about note-formatting preferences.
Categories: add_preference, update_preference, remove_preference, list_preferences, help, unknown.
Request: "{request}"
Respond with JSON only: {{"request_type": "...", "confidence": 0-100, "reasoning": "..."}}"""

IDENTIFY_PROMPT = """Identify note-processing preferences in the request (style, format, organisation, emphasis).
Current preferences: {current}
Request: "{request}"
Respond with JSON only:
{{"identified_preferences": {{"<name>": {{"value": "...", "confidence": 0-100, "explanation": "..."}}}}}}
Only include preferences clearly indicated and not already present."""

UPDATE_PROMPT = """The user wants to change existing preferences.
Current preferences: {current}
Request: "{request}"
Respond with JSON only:
{{"updates": {{"<existing name>": {{"value": "new value", "confidence": 0-100, "explanation": "..."}}}}}}"""

REMOVE_PROMPT = """The user wants to remove preferences.
Current preferences: {current}
Request: "{request}"
Respond with JSON only: {{"remove": ["<existing name>", ...], "confidence": 0-100}}"""


@dataclass
class PreferenceResult:
    action: str  # add | update | remove | list | help | none | error
    message: str
    saved: list[dict] = field(default_factory=list)
    suggested: list[dict] = field(default_factory=list)
    current: dict[str, str] = field(default_factory=dict)


def _json(text: str) -> dict:
    """Extract the first JSON object from a model reply; tolerate code fences and prose."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


class PreferenceService:
    def __init__(self, repo: PreferenceRepository, provider: LLMProvider, confidence_threshold: int = 80):
        self.repo = repo
        self.provider = provider
        self.threshold = confidence_threshold

    def current(self) -> dict[str, str]:
        return {p.key: p.value for p in self.repo.list()}

    def as_prompt_list(self) -> list[dict]:
        return [{"key": p.key, "value": p.value, "explanation": p.explanation} for p in self.repo.list()]

    def _ask(self, prompt: str) -> dict:
        reply = self.provider.chat([ChatMessage("system", "Reply with JSON only."), ChatMessage("user", prompt)],
                                   temperature=0.2, max_tokens=600)
        return _json(reply)

    def handle(self, request: str) -> PreferenceResult:
        request = request.strip()
        if not request:
            return PreferenceResult("none", "Empty request.", current=self.current())
        try:
            cls = self._ask(CLASSIFY_PROMPT.format(request=request))
        except LLMUnavailable as e:
            return PreferenceResult("error", str(e), current=self.current())
        kind = cls.get("request_type", "unknown")
        conf = int(cls.get("confidence", 0) or 0)
        if conf < self.threshold:
            kind = "add_preference"  # low confidence: fall through to identification, suggest only
        if kind == "list_preferences":
            return PreferenceResult("list", "Here are your current preferences.", current=self.current())
        if kind == "help":
            return PreferenceResult("help", HELP_TEXT, current=self.current())
        if kind == "update_preference":
            return self._update(request)
        if kind == "remove_preference":
            return self._remove(request)
        return self._add(request, auto_save=conf >= self.threshold)

    def _add(self, request: str, auto_save: bool) -> PreferenceResult:
        data = self._ask(IDENTIFY_PROMPT.format(current=json.dumps(self.current()), request=request))
        found = data.get("identified_preferences") or {}
        saved, suggested = [], []
        for name, d in found.items():
            if not isinstance(d, dict) or not d.get("value"):
                continue
            item = {"key": name, "value": str(d["value"]), "explanation": d.get("explanation", ""),
                    "confidence": int(d.get("confidence", 0) or 0)}
            if auto_save and item["confidence"] >= self.threshold:
                self.repo.set(name, item["value"], item["explanation"])
                saved.append(item)
            else:
                suggested.append(item)
        if not saved and not suggested:
            return PreferenceResult("none", "I couldn't identify a preference in that request.", current=self.current())
        msg = f"Saved {len(saved)} preference(s)." if saved else "Found possible preferences; confirm to save."
        return PreferenceResult("add", msg, saved=saved, suggested=suggested, current=self.current())

    def _update(self, request: str) -> PreferenceResult:
        data = self._ask(UPDATE_PROMPT.format(current=json.dumps(self.current()), request=request))
        saved = []
        for name, d in (data.get("updates") or {}).items():
            if isinstance(d, dict) and d.get("value") and self.repo.get(name) is not None:
                self.repo.set(name, str(d["value"]), d.get("explanation", ""))
                saved.append({"key": name, "value": str(d["value"]), "explanation": d.get("explanation", "")})
        msg = f"Updated {len(saved)} preference(s)." if saved else "No matching preference to update."
        return PreferenceResult("update", msg, saved=saved, current=self.current())

    def _remove(self, request: str) -> PreferenceResult:
        data = self._ask(REMOVE_PROMPT.format(current=json.dumps(self.current()), request=request))
        removed = [n for n in (data.get("remove") or []) if isinstance(n, str) and self.repo.delete(n)]
        msg = f"Removed: {', '.join(removed)}." if removed else "No matching preference to remove."
        return PreferenceResult("remove", msg, saved=[{"key": n} for n in removed], current=self.current())
