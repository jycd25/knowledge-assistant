from knowledge_assistant.core.llm.base import FakeProvider
from knowledge_assistant.core.qa import QAService
from knowledge_assistant.core.repositories import EntryRepository
from knowledge_assistant.core.search import HybridSearch


def test_qa_answers_with_sources_and_handles_no_hits(session, embedder):
    EntryRepository(session, embedder).create(title="Coffee", content="Espresso is brewed under nine bars of pressure.")
    qa = QAService(HybridSearch(session, embedder), FakeProvider(reply="Nine bars [1]."))
    a = qa.answer("how much pressure for espresso")
    assert a.text == "Nine bars [1]." and a.sources[0].entry_title == "Coffee"
    hits, stream = qa.stream("espresso pressure")
    assert hits and "".join(stream).strip() == "Nine bars [1]."
    assert qa.answer("zzzz qqqq").sources == []
