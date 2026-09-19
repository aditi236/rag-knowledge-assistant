import pytest

from app.chunker import chunk_document, chunk_text
from app.loader import Document


def test_short_text_is_a_single_chunk():
    assert chunk_text("Hello world.", size=100, overlap=10) == ["Hello world."]


def test_empty_text_gives_no_chunks():
    assert chunk_text("   \n\n  ", size=100, overlap=10) == []


def test_no_chunk_exceeds_size():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 40 for i in range(10))
    assert all(len(c) <= 200 for c in chunk_text(text, size=200, overlap=30))


def test_overlap_repeats_the_end_of_the_previous_chunk():
    text = "\n\n".join(f"Sentence number {i} is here." for i in range(20))
    chunks = chunk_text(text, size=120, overlap=30)
    assert len(chunks) > 1
    tail_words = chunks[0].split()[-2:]
    assert all(word in chunks[1] for word in tail_words)


def test_oversized_sentence_is_hard_split():
    chunks = chunk_text("x" * 450, size=200, overlap=20)
    assert len(chunks) == 3 and all(len(c) <= 200 for c in chunks)


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        chunk_text("text", size=50, overlap=50)


def test_chunk_document_numbers_chunks_and_keeps_source():
    document = Document(source="a.md", text="\n\n".join(["para " * 30] * 4))
    chunks = chunk_document(document, size=200, overlap=20)
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert {c.source for c in chunks} == {"a.md"}
