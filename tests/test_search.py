from knowledge_assistant.core.repositories import EntryRepository
from knowledge_assistant.core.search import HybridSearch, _fts_query


def _seed(session, embedder):
    entries = EntryRepository(session, embedder)
    entries.create(title="Relativity", content="Einstein's theory of relativity describes gravity and spacetime.")
    entries.create(title="Bread", content="Knead the sourdough dough, then proof it overnight before baking.")
    entries.create(title="Loose note", content="Quantum mechanics and spacetime are both physics topics.")


def test_hybrid_finds_keyword_and_vector_matches(session, embedder):
    _seed(session, embedder)
    hits = HybridSearch(session, embedder).search("spacetime gravity")
    titles = [h.entry_title for h in hits]
    assert titles[0] == "Relativity"
    assert "Bread" not in titles[:2]
    assert hits[0].keyword_rank is not None and hits[0].vector_rank is not None


def test_keyword_only_and_vector_only_modes(session, embedder):
    _seed(session, embedder)
    s = HybridSearch(session, embedder)
    kw = s.search("sourdough", mode="keyword")
    assert kw and kw[0].entry_title == "Bread" and kw[0].vector_rank is None
    vec = s.search("sourdough", mode="vector")
    assert vec and vec[0].keyword_rank is None


def test_fts_query_escapes_user_punctuation(session, embedder):
    _seed(session, embedder)
    assert _fts_query('what is "gravity"? AND OR NOT (x)') .count('"') % 2 == 0
    # must not raise on FTS syntax characters
    assert isinstance(HybridSearch(session, embedder).search('gravity? AND (x) "y'), list)


def test_empty_query_returns_nothing(session, embedder):
    assert HybridSearch(session, embedder).search("   ") == []
