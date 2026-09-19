"""A small in-memory vector store: brute-force cosine search, persisted to disk."""
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from app.chunker import Chunk


@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float


class VectorStore:
    def __init__(self) -> None:
        self._vectors: np.ndarray | None = None
        self._chunks: list[Chunk] = []

    def __len__(self) -> int:
        return len(self._chunks)

    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        if not chunks:
            return
        self._vectors = vectors if self._vectors is None else np.vstack([self._vectors, vectors])
        self._chunks.extend(chunks)

    def remove_source(self, source: str) -> None:
        keep = [i for i, chunk in enumerate(self._chunks) if chunk.source != source]
        if len(keep) == len(self._chunks):
            return
        self._chunks = [self._chunks[i] for i in keep]
        self._vectors = self._vectors[keep] if keep else None

    def search(self, query_vector: np.ndarray, top_k: int, min_score: float) -> list[SearchResult]:
        if self._vectors is None:
            return []
        scores = self._vectors @ query_vector
        best = np.argsort(-scores)[:top_k]
        return [SearchResult(self._chunks[i], float(scores[i])) for i in best if scores[i] >= min_score]

    def sources(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for chunk in self._chunks:
            counts[chunk.source] = counts.get(chunk.source, 0) + 1
        return counts

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        if self._vectors is None:
            (directory / "vectors.npy").unlink(missing_ok=True)
        else:
            np.save(directory / "vectors.npy", self._vectors)
        (directory / "chunks.json").write_text(
            json.dumps([asdict(chunk) for chunk in self._chunks]), encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: Path) -> "VectorStore":
        store = cls()
        chunks_file = directory / "chunks.json"
        if not chunks_file.exists():
            return store
        chunks = [Chunk(**item) for item in json.loads(chunks_file.read_text(encoding="utf-8"))]
        if chunks:
            store.add(chunks, np.load(directory / "vectors.npy"))
        return store
