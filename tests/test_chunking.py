from knowledge_assistant.core.chunking import chunk_text, estimate_tokens


def test_short_text_is_one_chunk():
    out = chunk_text("Hello world.")
    assert len(out) == 1 and out[0].ord == 0 and out[0].text == "Hello world."


def test_empty_text_no_chunks():
    assert chunk_text("   ") == []


def test_long_text_splits_with_overlap():
    text = " ".join(f"Sentence number {i} is here." for i in range(200))
    out = chunk_text(text, max_tokens=100, overlap_tokens=20)
    assert len(out) > 3
    assert all(c.token_count <= 100 for c in out)  # the budget is a ceiling, not a target
    assert [c.ord for c in out] == list(range(len(out)))
    # overlap: the start of chunk N+1 appears at the end of chunk N
    first_sentence_of_second = out[1].text.split(". ")[0]
    assert first_sentence_of_second in out[0].text


def test_single_huge_sentence_is_hard_split():
    text = "word " * 5000
    out = chunk_text(text, max_tokens=100, overlap_tokens=10)
    assert len(out) > 1
    assert all(estimate_tokens(c.text) <= 130 for c in out)


def test_overlap_must_be_smaller_than_max():
    import pytest
    with pytest.raises(ValueError):
        chunk_text("x", max_tokens=10, overlap_tokens=10)
