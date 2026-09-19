"""Retrieval evaluation: does the right document appear in the top-k results? (No LLM calls, no cost.)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):  # launched as a plain file, e.g. VS Code's "Run Python File" button
    sys.path.insert(0, str(ROOT))

from app.chunker import chunk_document  # noqa: E402
from app.config import Settings  # noqa: E402
from app.embeddings import FastEmbedEmbedder  # noqa: E402
from app.loader import load_directory  # noqa: E402
from app.vector_store import VectorStore  # noqa: E402


def main() -> None:
    settings = Settings()
    embedder = FastEmbedEmbedder(settings.embedding_model)
    store = VectorStore()
    for document in load_directory(ROOT / "data" / "sample_docs"):
        chunks = chunk_document(document, settings.chunk_size, settings.chunk_overlap)
        store.add(chunks, embedder.embed_documents([c.text for c in chunks]))

    pairs = json.loads((ROOT / "eval" / "qa_pairs.json").read_text(encoding="utf-8"))
    answerable = [p for p in pairs if p["expected_source"]]
    unanswerable = [p for p in pairs if not p["expected_source"]]

    hits, reciprocal_ranks = 0, []
    for pair in answerable:
        results = store.search(embedder.embed_query(pair["question"]), settings.top_k, min_score=0.0)
        sources = [r.chunk.source for r in results]
        rank = sources.index(pair["expected_source"]) + 1 if pair["expected_source"] in sources else None
        hits += rank is not None
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        print(f"{'PASS' if rank else 'FAIL'}  rank={rank}  {pair['question']}")

    refused = 0
    for pair in unanswerable:
        results = store.search(embedder.embed_query(pair["question"]), settings.top_k, settings.min_score)
        refused += not results
        print(f"{'PASS' if not results else 'FAIL'}  (should be refused)  {pair['question']}")

    print(f"\nhit@{settings.top_k}: {hits}/{len(answerable)} = {hits / len(answerable):.0%}")
    print(f"MRR: {sum(reciprocal_ranks) / len(answerable):.3f}")
    print(f"correctly refused at MIN_SCORE={settings.min_score}: {refused}/{len(unanswerable)}")


if __name__ == "__main__":
    main()
