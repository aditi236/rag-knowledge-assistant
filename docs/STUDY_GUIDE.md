# Study Guide

How to learn this project well enough to explain it, demo it, and defend it in an interview.
Read in this order: **(1) this page's pitch and concepts, (2) [ARCHITECTURE.md](ARCHITECTURE.md), (3) [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md), (4) do the exercises.**

---

## 1. The pitch

### 30 seconds
> "I built a document Q&A service using retrieval-augmented generation. Uploaded documents are split into overlapping chunks and embedded locally with a BGE model.
> When someone asks a question, I embed it, find the most similar chunks by cosine similarity, and pass only those to Claude with instructions to answer strictly from that context and cite sources.
> If nothing in the documents is similar enough, the system refuses without calling the model, which is my main defence against hallucination. I measured retrieval on a small eval set and calibrated the refusal threshold from real scores."

### 2 minutes (add these)
- "The stack is Python, FastAPI, a NumPy vector store I wrote so I understand exactly what a vector database does, fastembed for CPU embeddings, and the Anthropic SDK."
- "Everything is behind interfaces with dependency injection, so the tests use fake embedders and a fake LLM: 39 tests run in half a second with no network."
- "I evaluate retrieval separately from generation: hit@4 was 12 out of 12, and all 5 unanswerable questions were refused at the calibrated threshold."
- "It is containerised and configured through environment variables, so it is built to run on a container platform such as Azure Container Apps."
  *(Say "built to run", not "deployed", unless you have deployed it. See section 6.)*

---

## 2. Concepts you must be able to explain

| Term | Plain-English meaning | Where it appears |
|---|---|---|
| **RAG** | Look up relevant passages first, then have the model answer from them | The whole project |
| **Embedding** | A list of numbers (here 384) representing the *meaning* of text; similar meaning gives similar numbers | `embeddings.py` |
| **Cosine similarity** | How closely two vectors point in the same direction: 1 = same meaning, 0 = unrelated | `vector_store.search` |
| **Unit vector / normalisation** | Scaling a vector to length 1, so dot product = cosine similarity | `embeddings.unit_length` |
| **Chunking** | Splitting documents into small pieces so each embeds to a sharp meaning | `chunker.py` |
| **Overlap** | Repeating the end of one chunk at the start of the next so facts are not cut in half | `chunk_overlap` |
| **top-k** | How many best-matching chunks to retrieve | `TOP_K` (4) |
| **Similarity threshold** | Minimum score to count as relevant; below it the system says "not found" | `MIN_SCORE` (0.58) |
| **Grounding** | Forcing the answer to come from supplied context, not the model's memory | System prompt |
| **Hallucination** | The model stating something fluent but not supported by the sources | What the design defends against |
| **Citation** | Pointing to which source chunk supports each statement | `[1]`, `Citation` |
| **Asymmetric retrieval** | Short queries and long passages are encoded differently (BGE uses a query prefix) | `embed_query` vs `embed_documents` |
| **Vector database** | Storage plus fast nearest-neighbour search over vectors | `VectorStore` (brute force) |
| **ANN (approximate nearest neighbour)** | Trade a little accuracy for a big speed-up on huge collections (HNSW, IVF) | Scaling path |
| **Hybrid search** | Combine keyword (BM25) and vector search | Roadmap |
| **Re-ranking** | A second, more precise model re-orders the top results | Roadmap |
| **Prompt injection** | Text inside a document that tries to give the model new instructions | Security section |
| **hit@k** | Fraction of questions whose right document appears in the top k | `eval/run_eval.py` |
| **MRR** | Mean reciprocal rank: rewards putting the right document first (1, 0.5, 0.33, ...) | `eval/run_eval.py` |
| **Dependency injection** | Pass a class its collaborators instead of creating them inside | `RagPipeline.__init__` |

---

## 3. Trace one question by hand

Use this to prove you understand the flow. Real numbers from running the project:

**Question:** "What is the maximum I can spend on a hotel in London?"

1. `POST /ask` → pydantic checks length (1 to 2000). ✔
2. `ask()` → index has 6 chunks, so not empty. ✔
3. `embed_query` → a 384-number unit vector.
4. `search` → matrix (6 x 384) times vector (384) gives 6 scores. Best: `expenses-policy.md` chunk 1 with a score of about 0.65 to 0.73 (the CLI showed 0.6455 for a similar hotel question). Threshold 0.58 → passes.
5. The prompt sent to Claude:
   ```
   <context>
   [1] (source: expenses-policy.md)
   ...Hotel stays are capped at USD 220 per night in tier-1 cities (London, New York, Singapore, Dubai)...
   [2] (source: ...)
   </context>

   Question: What is the maximum I can spend on a hotel in London?
   ```
6. Claude answers something like "USD 220 per night [1]".
7. Response: `{answer, grounded: true, citations: [{source, chunk_index, score, text}, ...]}`.

**Question:** "How do I bake sourdough bread?" → best score 0.43, below 0.58 → `{"answer": "I couldn't find that in the provided documents.", "grounded": false}` and **no model call**.

---

## 4. Interview questions and model answers

**Q1. Why RAG instead of fine-tuning?**
Fine-tuning bakes knowledge into weights: expensive, hard to update, no citations. RAG keeps knowledge in a searchable store: update by re-uploading a file, cite the source, cheap. Fine-tuning suits changing *style or behaviour*; RAG suits changing *knowledge*.

**Q2. What is an embedding and why does cosine similarity work?**
A model maps text to a point in a high-dimensional space trained so that similar meanings land close together. Direction encodes meaning, so the angle between vectors (cosine) measures semantic closeness regardless of text length.

**Q3. Why did you normalise the vectors?**
With unit vectors, dot product equals cosine similarity, so retrieval is one matrix multiplication and scores are on a comparable scale.

**Q4. How did you choose chunk size and overlap?**
800 characters (a few paragraphs) with 120 overlap is a common starting point: big enough to hold a complete idea, small enough to embed sharply. I did not claim it is optimal; the right way to tune it is to change it and re-run the retrieval eval. Overlap protects facts that straddle a boundary.

**Q5. How do you stop hallucinations?**
Three layers: (1) a similarity threshold that refuses before calling the model when nothing relevant exists; (2) a strict prompt: answer only from the numbered context, with an exact refusal sentence; (3) citations, so a human can verify. None is a guarantee; the model can still mis-cite, which is why I would add automated faithfulness checks next.

**Q6. How did you pick the threshold?**
I measured it. Off-topic questions scored up to 0.52; real questions scored at least 0.64. I set 0.58 in the gap. My first guess of 0.45 would have let the CEO-salary and stock-price questions through, which is why I measured. It is specific to this model and corpus and must be recalibrated when either changes.

**Q7. Why did you write your own vector store?**
To understand and be able to explain exactly what one does: a matrix of vectors, a matrix-vector product, sort, top-k. At this scale brute force is exact and fast. It sits behind a small interface, so I would replace it with FAISS, pgvector or Azure AI Search when the corpus outgrows RAM or I need filtering, concurrency or persistence guarantees.

**Q8. How would you scale it to millions of documents?**
Approximate nearest-neighbour index or a managed vector database; move ingestion to a background worker; stateless API replicas; per-tenant filtering; hybrid search and re-ranking to keep quality as the corpus grows.

**Q9. How do you evaluate a RAG system?**
Separate the two halves. **Retrieval:** is the right chunk in the top-k? (hit@k, MRR): cheap, no LLM cost. Include **unanswerable** questions to test refusal. **Generation:** is the answer faithful to the retrieved context and complete? That needs an LLM-as-judge or human review, which I have not automated yet.

**Q10. What are RAG's typical failure modes?**
Bad chunking splits the answer; the right chunk is not retrieved (vocabulary mismatch, wrong `top_k`); the retriever returns plausible but wrong chunks; the model ignores the context or over-generalises; contradictory documents; stale index; prompt injection in documents.

**Q11. Why a separate query embedding method?**
BGE is an asymmetric retrieval model: short questions and long passages are encoded slightly differently (queries get an instruction prefix). Using the wrong one lowers retrieval quality.

**Q12. Why are the endpoints `def` and not `async def`?**
The work is blocking (CPU embedding, a synchronous SDK call). FastAPI runs plain `def` endpoints in a thread pool, so they do not block the event loop. An `async def` that does blocking work would freeze the whole server for everyone.

**Q13. Why dependency injection?**
The pipeline is constructed with an embedder, store and LLM instead of creating them. That lets tests use a hash-based fake embedder and a recording fake LLM, so the suite is fast, offline and deterministic, and lets me swap any component without touching the pipeline.

**Q14. What happens when Claude is down or rate-limited?**
The SDK already retries transient errors. If it still fails, I map errors by type: 429 for rate limit (client should retry), 503 for connection failure, 502 for other upstream errors, 500 with a generic message for bad credentials. The specific handlers come first because those exceptions are subclasses of the general one.

**Q15. What is prompt injection, and is your system vulnerable?**
It is when text inside a document tries to override your instructions. Any RAG system is exposed. I reduce the risk (delimited context, rules in the system prompt) but do not eliminate it, and I would not connect this to tools with side effects over untrusted documents.

**Q16. What would you improve first?**
(1) A lock and atomic writes for concurrent ingestion; (2) hybrid search plus a re-ranker; (3) an automated faithfulness eval; (4) conversation memory; (5) authentication and per-tenant indexes; (6) OCR for scanned PDFs.

**Q17. What is the cost of one query?**
Roughly 1,000 to 1,500 input tokens (question, system prompt, up to four ~200-token chunks) plus the answer: well under a cent at current Claude pricing. Refused questions cost nothing because the model is never called. A smaller model is one environment variable away.

**Q18. Why local embeddings rather than an API?**
No extra vendor or key, documents are not sent out for embedding, works offline, no per-call cost. The trade-off is a somewhat lower ceiling than the largest hosted models, and I have to ship and cache the model.

**Q19. Why does the extractive fallback exist?**
So the whole system runs and can be demoed and tested with no API key or cost, and it proves the retrieval half works independently of the LLM.

**Q20. What did you learn while building it?**
That a guessed similarity threshold was wrong and only measurement fixed it; and that measuring retrieval separately from generation tells you where a bad answer came from.

---

## 5. Demo script (5 minutes)

```bash
# 1. Setup (once)
python -m venv .venv && .venv\Scripts\activate        # Windows; use source .venv/bin/activate on Mac/Linux
pip install -r requirements-dev.txt

# 2. Show the tests and the retrieval eval
pytest -q                                              # 39 passed
python -m eval.run_eval                                # hit@4 12/12, MRR 0.958, 5/5 refused

# 3. Index the sample documents and ask (works offline)
set LLM_PROVIDER=extractive
python -m app.cli ingest data/sample_docs
python -m app.cli ask "What is the hotel cap in London?"
python -m app.cli ask "How do I bake sourdough bread?"     # refused, no model call

# 4. With Claude (set a real key first)
set ANTHROPIC_API_KEY=sk-ant-...
set LLM_PROVIDER=auto
python -m app.cli ask "Can I use my personal ChatGPT account for client work?"

# 5. The API
uvicorn app.api:app --port 8000                        # then open http://localhost:8000/docs
```

**Talking points while demoing:** show a citation and its score; show the refused question and say "no model call, no cost, no hallucination";
open `config.py` and show `MIN_SCORE`, then explain the calibration table from ARCHITECTURE section 8.

---

## 6. Being honest about what this is (important for interviews)

- The **sample documents are synthetic** ("Northwind Consulting" is fictional). Say so.
- The **retrieval eval is small** (12 + 5 questions). It catches regressions; it does not prove production quality.
- The **Claude call path** is unit-tested with a stub client (request shape, refusal handling, text extraction). Before you demo it live, **run one real question with your API key** so you have seen it work end to end.
- The **Docker image was not build-tested** on the machine this was written on. Run `docker build .` before claiming it works.
- It has **not been deployed** to Azure or anywhere else. Say "built to be deployed as a container" not "deployed on Azure".
- You can truthfully say: built, tested, evaluated, containerised (after you have built the image), documented. Do not claim scale, users or production traffic.

---

## 7. Exercises (do these; they are how it sticks)

1. **Break the threshold.** Set `MIN_SCORE=0.4`, run the eval, and see which unanswerable questions now leak through. Set it to 0.8 and see which real questions get refused.
2. **Tune chunking.** Try `CHUNK_SIZE=300` and `1500`; re-run the eval; compare hit@4 and MRR. Explain the result.
3. **Add your own documents.** Put a real PDF in `data/`, ingest it, write 10 questions and add them to `eval/qa_pairs.json`.
4. **Implement a metadata filter:** `search(..., source="expenses-policy.md")`.
5. **Add BM25 keyword search** (e.g. `rank_bm25`) and fuse it with vector scores (reciprocal rank fusion). Add an eval question containing an exact code that vectors struggle with.
6. **Add a re-ranker** (a cross-encoder) over the top 10 results, keeping 4.
7. **Streaming:** use the SDK's streaming interface and return server-sent events from `/ask`.
8. **Conversation memory:** rewrite a follow-up question into a standalone question before retrieval.
9. **Swap the vector store** for FAISS behind the same interface without changing `rag.py`.
10. **Write an LLM-judge faithfulness check** that scores whether each claim in an answer is supported by its cited chunks.
11. **Fix limitation 2** (ingest atomicity) and write the failing test first.
12. **Deploy it** to a container platform and put a real URL on your CV. Then it is a true statement.
