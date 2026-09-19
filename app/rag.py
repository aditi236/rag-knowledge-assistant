"""The RAG pipeline: ingest documents, then retrieve and generate grounded answers."""
from dataclasses import dataclass
from pathlib import Path

from app.chunker import chunk_document
from app.config import Settings
from app.embeddings import Embedder, FastEmbedEmbedder
from app.llm import LLM, NOT_FOUND_MESSAGE, build_llm
from app.loader import Document
from app.vector_store import VectorStore


@dataclass(frozen=True)
class Citation:
    source: str
    chunk_index: int
    score: float
    text: str


@dataclass(frozen=True)
class Answer:
    answer: str
    grounded: bool
    citations: list[Citation]


class RagPipeline:
    def __init__(self, embedder: Embedder, store: VectorStore, llm: LLM, settings: Settings):
        self.embedder = embedder
        self.store = store
        self.llm = llm
        self.settings = settings

    def ingest(self, documents: list[Document]) -> dict[str, int]:
        total_chunks = 0
        for document in documents:
            self.store.remove_source(document.source)
            chunks = chunk_document(document, self.settings.chunk_size, self.settings.chunk_overlap)
            if not chunks:
                continue
            vectors = self.embedder.embed_documents([chunk.text for chunk in chunks])
            self.store.add(chunks, vectors)
            total_chunks += len(chunks)
        self.store.save(self.settings.index_dir)
        return {"documents": len(documents), "chunks": total_chunks}

    def ask(self, question: str) -> Answer:
        if len(self.store) == 0:
            return Answer("No documents have been ingested yet.", False, [])
        query_vector = self.embedder.embed_query(question)
        results = self.store.search(query_vector, self.settings.top_k, self.settings.min_score)
        if not results:
            return Answer(NOT_FOUND_MESSAGE, False, [])
        text = self.llm.generate(question, results)
        citations = [
            Citation(r.chunk.source, r.chunk.index, round(r.score, 4), r.chunk.text) for r in results
        ]
        return Answer(text, True, citations)


def build_pipeline(settings: Settings) -> RagPipeline:
    embedder = FastEmbedEmbedder(settings.embedding_model)
    store = VectorStore.load(Path(settings.index_dir))
    return RagPipeline(embedder, store, build_llm(settings), settings)
