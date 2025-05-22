from knowledge_assistant.core import notes
from knowledge_assistant.core.llm.base import FakeProvider, NullProvider
from knowledge_assistant.core.preferences import PreferenceService
from knowledge_assistant.core.qa import QAService
from knowledge_assistant.core.repositories import EntryRepository, PreferenceRepository
from knowledge_assistant.core.search import HybridSearch
from knowledge_assistant.core.templates import BUILTIN_TEMPLATES, get_builtin

LONG = ("Today I learned about photosynthesis in plants. Chlorophyll absorbs light energy. "
        "The Calvin cycle fixes carbon into sugars. However, respiration releases that energy again. "
        "Mitochondria are the site of respiration. ") * 4


def test_heuristic_note_has_title_sections_tags_summary():
    out = notes.process_heuristic(LONG)
    assert out.title and "Photosynthesis" in out.title
    assert out.markdown.startswith("# ")
    assert "## Summary" in out.markdown and "## Tags" in out.markdown
    assert "#Energy" in out.tags  # most frequent non-stopword
    assert not out.used_llm


def test_llm_note_uses_prompt_with_preferences_and_falls_back():
    fake = FakeProvider(reply="# LLM Title\n\n## Summary\nx\n\n## Tags\n#Alpha #Beta")
    out = notes.process_with_llm("some text", fake, user_request="be brief",
                                 preferences=[{"key": "style", "value": "casual", "explanation": ""}])
    assert out.title == "LLM Title" and out.tags == ["#Alpha", "#Beta"] and out.used_llm
    prompt = fake.calls[0][-1].content
    assert "style: casual" in prompt and "be brief" in prompt and "some text" in prompt
    fallback = notes.process_with_llm(LONG, NullProvider())
    assert not fallback.used_llm and fallback.markdown.startswith("# ")


def test_preference_chain_add_list_remove(session):
    repo = PreferenceRepository(session)
    fake = FakeProvider()
    svc = PreferenceService(repo, fake, confidence_threshold=80)

    fake.reply = '{"request_type":"add_preference","confidence":95}'
    # second call (identify) gets the same reply object; emulate by swapping reply between calls
    class Seq(FakeProvider):
        def __init__(self, replies): super().__init__(); self.replies = list(replies)
        def chat(self, messages, **kw):
            self.calls.append(messages)
            return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
    svc.provider = Seq(['{"request_type":"add_preference","confidence":95}',
                        '{"identified_preferences":{"style":{"value":"bullet points","confidence":90,"explanation":"asked"}}}'])
    r = svc.handle("I want bullet points")
    assert r.action == "add" and r.saved[0]["key"] == "style" and repo.get("style").value == "bullet points"

    svc.provider = Seq(['{"request_type":"add_preference","confidence":95}',
                        '{"identified_preferences":{"tone":{"value":"formal","confidence":50,"explanation":""}}}'])
    r = svc.handle("maybe formal?")
    assert r.suggested and not r.saved and repo.get("tone") is None  # low confidence never auto-saves

    svc.provider = Seq(['{"request_type":"list_preferences","confidence":99}'])
    assert svc.handle("show prefs").current == {"style": "bullet points"}

    svc.provider = Seq(['{"request_type":"remove_preference","confidence":99}', '{"remove":["style"],"confidence":95}'])
    r = svc.handle("drop bullet points")
    assert r.action == "remove" and repo.get("style") is None

    svc.provider = Seq(["not json at all"])
    assert svc.handle("???").action in ("none", "add")  # garbage reply never raises


def test_qa_answers_with_sources_and_handles_no_hits(session, embedder):
    EntryRepository(session, embedder).create(title="Coffee", content="Espresso is brewed under nine bars of pressure.")
    qa = QAService(HybridSearch(session, embedder), FakeProvider(reply="Nine bars [1]."))
    a = qa.answer("how much pressure for espresso")
    assert a.text == "Nine bars [1]." and a.sources[0].entry_title == "Coffee"
    hits, stream = qa.stream("espresso pressure")
    assert hits and "".join(stream).strip() == "Nine bars [1]."
    assert qa.answer("zzzz qqqq").sources == []


def test_builtin_templates():
    assert set(BUILTIN_TEMPLATES) == {"basic", "meeting", "project", "research", "study"}
    assert get_builtin("nope") == BUILTIN_TEMPLATES["basic"]
    assert all(t.startswith("# ") for t in BUILTIN_TEMPLATES.values())
