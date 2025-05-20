from knowledge_assistant.core import notes
from knowledge_assistant.core.llm.base import FakeProvider, NullProvider
from knowledge_assistant.core.qa import QAService
from knowledge_assistant.core.repositories import EntryRepository
from knowledge_assistant.core.search import HybridSearch

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


def test_qa_answers_with_sources_and_handles_no_hits(session, embedder):
    EntryRepository(session, embedder).create(title="Coffee", content="Espresso is brewed under nine bars of pressure.")
    qa = QAService(HybridSearch(session, embedder), FakeProvider(reply="Nine bars [1]."))
    a = qa.answer("how much pressure for espresso")
    assert a.text == "Nine bars [1]." and a.sources[0].entry_title == "Coffee"
    hits, stream = qa.stream("espresso pressure")
    assert hits and "".join(stream).strip() == "Nine bars [1]."
    assert qa.answer("zzzz qqqq").sources == []
