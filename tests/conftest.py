"""Shared test doubles: a deterministic fake embedder and a recording fake LLM (no downloads, no API calls)."""
import hashlib
import re

import numpy as np
import pytest

from app.config import Settings
from app.embeddings import unit_length
from app.rag import RagPipeline
from app.vector_store import VectorStore

DIM = 512


class FakeEmbedder:
    """Bag-of-words hashing embedder: texts sharing words get similar vectors."""

    def _embed(self, text: str) -> np.ndarray:
        vector = np.zeros(DIM, dtype=np.float32)
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
        return vector

    def embed_documents(self, texts):
        return unit_length(np.stack([self._embed(t) for t in texts]))

    def embed_query(self, text):
        return unit_length(self._embed(text))


class FakeLLM:
    def __init__(self):
        self.calls = []

    def generate(self, question, results):
        self.calls.append((question, results))
        return "fake answer [1]"


@pytest.fixture
def settings(tmp_path):
    return Settings(index_dir=tmp_path / "index", chunk_size=300, chunk_overlap=40, top_k=3, min_score=0.2)


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def pipeline(settings, fake_llm):
    return RagPipeline(FakeEmbedder(), VectorStore(), fake_llm, settings)
