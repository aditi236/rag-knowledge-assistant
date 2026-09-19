import numpy as np
import pytest

from app.chunker import Chunk
from app.vector_store import VectorStore


def make_store():
    chunks = [Chunk("a.md", 0, "alpha"), Chunk("a.md", 1, "beta"), Chunk("b.md", 0, "gamma")]
    vectors = np.array([[1, 0, 0], [0, 1, 0], [0.6, 0.8, 0]], dtype=np.float32)
    store = VectorStore()
    store.add(chunks, vectors)
    return store


def test_search_returns_best_match_first():
    results = make_store().search(np.array([1, 0, 0], dtype=np.float32), top_k=3, min_score=0.0)
    assert [r.chunk.text for r in results] == ["alpha", "gamma", "beta"]
    assert results[0].score == pytest.approx(1.0)


def test_min_score_filters_weak_matches():
    results = make_store().search(np.array([1, 0, 0], dtype=np.float32), top_k=3, min_score=0.5)
    assert [r.chunk.text for r in results] == ["alpha", "gamma"]


def test_top_k_limits_results():
    assert len(make_store().search(np.array([1, 0, 0], dtype=np.float32), top_k=1, min_score=0.0)) == 1


def test_remove_source_drops_only_that_source():
    store = make_store()
    store.remove_source("a.md")
    assert store.sources() == {"b.md": 1}


def test_empty_store_returns_nothing():
    assert VectorStore().search(np.array([1, 0, 0], dtype=np.float32), 3, 0.0) == []


def test_add_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        VectorStore().add([Chunk("a", 0, "x")], np.zeros((2, 3), dtype=np.float32))


def test_save_and_load_round_trip(tmp_path):
    store = make_store()
    store.save(tmp_path)
    loaded = VectorStore.load(tmp_path)
    assert loaded.sources() == store.sources()
    query = np.array([1, 0, 0], dtype=np.float32)
    assert [r.chunk for r in loaded.search(query, 3, 0.0)] == [r.chunk for r in store.search(query, 3, 0.0)]
