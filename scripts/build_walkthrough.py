"""Generate docs/CODE_WALKTHROUGH.md: every source line, shown with its real line number and explained.

The code listings are read from the actual files, so they can never drift from the source.
The script FAILS if any non-blank line of a documented file has no explanation, or if an annotation
points at lines that do not exist. After you edit code, re-run this and fix any complaint:

    python scripts/build_walkthrough.py
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "CODE_WALKTHROUGH.md"

# ---------------------------------------------------------------------------------------------
# Core application code: line-range annotations, (first_line, last_line, explanation).
# ---------------------------------------------------------------------------------------------
APP = {}

APP["app/config.py"] = (
    r"""Central configuration. Every tunable number in the system lives here, read from environment
variables, so behaviour changes without code changes (the "12-factor app" rule: config in the environment).""",
    [
        (1, 1, r"""Module docstring. "12-factor style" means configuration comes from environment variables, never hard-coded, so the same container image runs in dev, test and production."""),
        (2, 4, r"""Imports. `os` reads environment variables. `dataclass` gives us a tidy settings object. `Path` is the standard way to represent file-system paths (works on Windows and Linux)."""),
        (6, 8, r"""`load_dotenv()` reads a local `.env` file (if one exists) into the process environment. It must run **before** the `Settings` class is defined, because the defaults below are evaluated once, when the class is created. In production (Docker/Azure) there is no `.env`; the platform injects real environment variables and this call quietly does nothing."""),
        (10, 11, r"""`ROOT` is the project folder (found relative to this file, so it works from any working directory). `ON_VERCEL` is true when the platform sets the `VERCEL` environment variable. **Why it matters:** a Vercel function's disk is **read-only except `/tmp`**, and `/tmp` is wiped whenever an instance is recycled, so paths that write (the index, the model cache) must move there."""),
        (18, 18, r"""**Where the embedding model is cached.** `None` means "fastembed's default" locally; on Vercel it is `/tmp/fastembed` (writable). The first request on a fresh instance downloads the model (about 65 MB) into it, which is why a cold start takes around 15 seconds."""),
        (19, 19, r"""**Seed folder.** If set, and the index is empty at start-up, the documents in this folder are indexed automatically. Off locally (empty string); on Vercel it points at the bundled `data/sample_docs`, because an ephemeral instance always starts with an empty index and would otherwise have nothing to answer from."""),
        (14, 15, r"""`@dataclass(frozen=True)` makes `Settings` an immutable record: once created, nobody can change a value by accident while the app runs. Tests create their own `Settings(...)` with overrides instead of touching globals."""),
        (16, 16, r"""**Where the index is saved.** `os.getenv("INDEX_DIR", "storage/index")` means "use the env var if set, otherwise this default". On Vercel the default is `/tmp/rag-index`, because that is the only writable place there."""),
        (17, 17, r"""**Embedding model.** `bge-small-en-v1.5` produces 384-number vectors, runs on a plain CPU, and downloads as a small ONNX file. It is a strong quality-for-size choice. Changing it means re-indexing everything (vectors from different models are not comparable) and re-calibrating `MIN_SCORE`."""),
        (20, 20, r"""**Which answer generator to use:** `auto` (Claude if an API key exists, else the offline extractive fallback), or force `claude` / `extractive`."""),
        (21, 21, r"""**Which Claude model.** Defaults to `claude-opus-5`. Set `LLM_MODEL=claude-sonnet-5` for a cheaper option; no code change needed."""),
        (22, 23, r"""**Chunking knobs.** `chunk_size` is in characters (800 is roughly 150 to 200 words, about 200 tokens). `chunk_overlap` (120, about 15%) repeats the end of one chunk at the start of the next, so a fact that straddles a boundary still appears whole in at least one chunk."""),
        (24, 24, r"""**`top_k`: how many chunks are retrieved** and sent to the model. Too small: you miss the answer. Too large: you pay for noise and distract the model."""),
        (25, 25, r"""**`min_score`: the "I don't know" threshold.** Retrieval always returns the *closest* chunks even for nonsense questions, so we need a cut-off. It was calibrated on the sample data: off-topic questions scored up to 0.52, genuine matches scored 0.64 or more, so 0.58 sits in the gap. This number depends on the embedding model and the corpus; re-measure with `python -m eval.run_eval` if either changes."""),
        (26, 26, r"""Maximum tokens Claude may produce. This budget also covers the model's internal reasoning on models that think by default, so it is set generously (4096) to avoid truncated answers."""),
    ],
)

APP["app/loader.py"] = (
    r"""Turns raw files into plain text. It is the only module that knows about file formats.""",
    [
        (1, 1, r"""Docstring: the loader's whole job is *files in, `Document` objects out*."""),
        (2, 4, r"""`io` lets us wrap raw bytes so libraries can read them like a file. `dataclass` and `Path` as before."""),
        (6, 6, r"""`pypdf` extracts text from PDF files (pure Python, no system dependencies)."""),
        (8, 8, r"""The set of supported extensions is defined **once** here and reused by both the CLI folder-walk and the API upload check, so they can never disagree."""),
        (11, 14, r"""`Document` is the unit of ingestion: `source` is the file name (used as the human-readable citation label *and* as the identity that lets re-uploading a file replace the old version), `text` is its content. `frozen=True` = immutable."""),
        (17, 17, r"""`extract_text` takes the filename and the file's **bytes**, not a path. That one design choice lets the same function serve files on disk (CLI) and uploads over HTTP (API)."""),
        (18, 18, r"""Look at the file extension in lower case, so `REPORT.PDF` works too."""),
        (19, 21, r"""PDF branch. `io.BytesIO(data)` makes the bytes look like an open file. Each page's `extract_text()` can return `None` (for example scanned images with no text layer), hence `or ""`. Pages are joined with a blank line so the chunker later sees them as separate paragraphs. **Limitation:** scanned PDFs need OCR, which is not implemented."""),
        (22, 23, r"""Text/Markdown branch: decode as UTF-8. `errors="replace"` swaps any bad byte for a placeholder character instead of crashing the whole ingest."""),
        (24, 24, r"""Any other type raises `ValueError`. The API turns this into an HTTP 422 response."""),
        (27, 28, r"""`load_bytes` builds a `Document`. `Path(filename).name` keeps only the final file name and strips any folder parts: a **security** measure so an upload named `../../etc/passwd` cannot smuggle path components into the stored source name."""),
        (31, 36, r"""`load_directory` walks a folder for the CLI. `rglob("*")` is recursive; `sorted(...)` makes the order deterministic, so chunk numbering is reproducible between runs; the `if` keeps only real files with a supported extension; each is read and passed through `load_bytes`. **Limitation:** two files with the same name in different sub-folders would collide, because `source` is just the file name."""),
    ],
)

APP["app/chunker.py"] = (
    r"""Chunking: splitting a long document into pieces small enough to embed and retrieve precisely.
Why? A whole 30-page handbook has one blurry "average meaning" vector; small focused chunks have sharp ones.""",
    [
        (1, 1, r"""Docstring: chunks are bounded in size, overlap slightly, and prefer to break at paragraph and sentence edges rather than mid-sentence."""),
        (2, 5, r"""`re` for regular expressions; `dataclass`; and `Document` from the loader, the input to chunking."""),
        (8, 12, r"""`Chunk` is what actually gets embedded and stored. `source` = which file; `index` = the chunk's position within that file (shown in citations, e.g. "expenses-policy.md, chunk 1"); `text` = the content."""),
        (15, 15, r"""`_split_units` (leading underscore = internal helper) breaks text into **units**, each no longer than `size`. Units are the smallest pieces the packer below is allowed to work with."""),
        (16, 16, r"""Start with an empty list of units."""),
        (17, 17, r"""`re.split(r"\n\s*\n", text)` splits on blank lines, i.e. into paragraphs."""),
        (18, 20, r"""Trim whitespace; skip empty paragraphs (for example from several blank lines in a row)."""),
        (21, 23, r"""If the whole paragraph fits, keep it intact: a paragraph is the most natural unit of meaning, so we avoid cutting it. `continue` jumps to the next paragraph."""),
        (24, 24, r"""The paragraph is too long, so split it into sentences. The pattern `(?<=[.!?])\s+` is a *lookbehind*: split on whitespace that comes right after `.`, `!` or `?`, keeping the punctuation with its sentence. **Limitation:** it is naive; "Dr. Smith" or "3.5" also trigger splits. A production system might use an NLP sentence splitter."""),
        (25, 27, r"""If a single sentence is *still* longer than `size` (a huge table row, minified text), hard-cut it every `size` characters. This guarantees no unit ever exceeds the limit."""),
        (28, 29, r"""Keep whatever is left of the sentence after cutting (if anything)."""),
        (30, 30, r"""Return the list of units."""),
        (33, 33, r"""`_overlap_tail` returns the last few characters of a finished chunk, to be repeated at the start of the next one."""),
        (34, 35, r"""If overlap is 0 (disabled) return an empty string."""),
        (36, 36, r"""Take the last `overlap` characters. `text[-120:]` is Python's negative slicing: "the final 120 characters"."""),
        (37, 38, r"""Find the first space and drop everything before it, so the overlap starts on a **whole word** instead of half a word like "ployees". If the tail has no space at all, keep it as is."""),
        (41, 41, r"""`chunk_text` is the main algorithm: pack units greedily into chunks of at most `size` characters. Defaults match the config defaults."""),
        (42, 43, r"""**Guard clause.** If overlap were as large as the chunk itself, each new chunk would be mostly a copy of the previous one and the algorithm would make no progress, so we reject that configuration up front."""),
        (44, 45, r"""`chunks` collects finished chunks; `current` is the chunk being built (a buffer)."""),
        (46, 46, r"""Go through the units in order."""),
        (47, 47, r"""`candidate` is what `current` would look like if we appended this unit, separated by a blank line to preserve paragraph structure. If the buffer is empty, the candidate is just the unit."""),
        (48, 50, r"""It still fits within `size`: accept it into the buffer and move on to the next unit."""),
        (51, 51, r"""It does **not** fit, so the buffer is full: emit it as a finished chunk. (The buffer cannot be empty here: an empty buffer makes the candidate equal to a single unit, which is at most `size`, so we would have taken the branch above.)"""),
        (52, 52, r"""Compute the overlap: the tail of the chunk we just finished."""),
        (53, 53, r"""The next chunk starts with that tail followed by the unit that did not fit."""),
        (54, 54, r"""Safety check: if tail plus unit would itself exceed `size`, drop the overlap for this chunk and start with just the unit. The size limit always wins."""),
        (55, 56, r"""After the loop, flush the final partially filled buffer as the last chunk."""),
        (57, 57, r"""Return all chunks as plain strings."""),
        (60, 62, r"""`chunk_document` wraps each string in a `Chunk` object carrying its source file and position (`enumerate` supplies 0, 1, 2, ...). This metadata is what makes citations possible later."""),
    ],
)

APP["app/embeddings.py"] = (
    r"""Embeddings: turning text into a list of numbers (a vector) such that texts with similar *meaning* get similar vectors.
This is what lets us search by meaning instead of by keyword.""",
    [
        (1, 1, r"""Docstring: the rest of the system only knows the `Embedder` interface, never the concrete library."""),
        (2, 2, r"""`Protocol` lets us declare an interface by shape ("anything with these methods") without inheritance."""),
        (4, 4, r"""NumPy: fast arrays and the maths for vectors."""),
        (7, 10, r"""The `Embedder` interface has **two** methods on purpose. `embed_documents` encodes many passages at once (batching is far faster than one at a time). `embed_query` encodes a single question. They are separate because *asymmetric* retrieval models such as BGE process queries differently from passages (a short question must be matched against long passages). Because it is a `Protocol`, the tests plug in a `FakeEmbedder`, and you could swap in Azure OpenAI or Voyage embeddings without touching the pipeline. The `...` bodies mean "no implementation here, this is only a contract"."""),
        (13, 15, r"""`unit_length` scales every vector to length 1 (L2 normalisation). `np.linalg.norm(..., axis=-1, keepdims=True)` computes each vector's length; `np.clip(norms, 1e-12, None)` prevents division by zero; dividing gives length-1 vectors. **Why it matters:** for unit vectors, the plain dot product *equals* cosine similarity, so search later is one matrix multiplication, and scores land in a comparable range. `axis=-1` makes it work for one vector (query) or a batch (documents)."""),
        (18, 18, r"""The real embedder, backed by the `fastembed` library (ONNX runtime, CPU-only, no PyTorch needed)."""),
        (19, 22, r"""Constructor. `cache_dir` (optional) says where the model files are stored; the pipeline passes `/tmp/fastembed` on Vercel because that is the only writable folder. The import sits **inside** the method (a *lazy import*), so importing this module, and running unit tests, does not load the heavy library or trigger a model download. `TextEmbedding(...)` downloads the model the first time (cached afterwards) and loads it into memory."""),
        (24, 26, r"""`embed_documents`: `self._model.embed(texts)` returns a generator of arrays; `list(...)` runs it; `np.array(..., dtype=np.float32)` makes an `(n_texts, 384)` matrix in 32-bit floats (half the memory of the default 64-bit, precision is ample). Then normalise to unit length."""),
        (28, 30, r"""`embed_query`: `query_embed` applies the model's special *query instruction prefix* (BGE models are trained with one). It also returns a generator; `next(iter(...))` takes the single vector. The result has shape `(384,)`, normalised."""),
    ],
)

APP["app/vector_store.py"] = (
    r"""The vector store: holds every chunk's vector and answers "which chunks are most similar to this query vector?".
It is intentionally a small, readable, brute-force implementation (a NumPy matrix) so you can explain exactly what a vector database does.""",
    [
        (1, 1, r"""Docstring. "Brute-force" means comparing the query against **every** stored vector: exact, simple, and fast enough for tens of thousands of chunks."""),
        (2, 4, r"""`json` for saving chunk text; `asdict` converts a dataclass to a dictionary; `dataclass`; `Path`."""),
        (6, 8, r"""NumPy for the matrix maths, and `Chunk` from the chunker."""),
        (11, 14, r"""`SearchResult` pairs a chunk with its similarity `score` (cosine similarity, between -1 and 1; higher = more similar)."""),
        (17, 20, r"""The store keeps two **parallel** structures: `_vectors`, an `(n_chunks, dim)` matrix (or `None` until the first add, because the vector dimension is not known in advance), and `_chunks`, a list of the matching chunk objects. **Invariant:** row `i` of the matrix is the vector for `_chunks[i]`. Every method must preserve this."""),
        (22, 23, r"""`__len__` makes `len(store)` work; the pipeline uses it to detect an empty index."""),
        (25, 27, r"""`add` first checks the invariant: same number of chunks and vectors."""),
        (28, 29, r"""Nothing to add? Do nothing. This also protects the `vstack` below from an empty array."""),
        (30, 31, r"""First add: the matrix *is* the given vectors. Later adds: `np.vstack` stacks the new rows below the old ones (this copies the array, O(n) per add: fine at this scale; a real vector DB uses an incremental index). Then extend the chunk list in the same order."""),
        (33, 34, r"""`remove_source` deletes all chunks of one file. First compute `keep`: the row numbers of chunks that belong to *other* files. **Why this exists:** re-uploading an edited file must replace its old chunks, not add duplicates."""),
        (35, 36, r"""If nothing would be removed, return early. This makes the operation idempotent (safe to call for a file that was never ingested)."""),
        (37, 38, r"""Rebuild the chunk list, and select the surviving matrix rows with fancy indexing (`matrix[[0, 2, 5]]`). If nothing remains, reset to `None`."""),
        (40, 42, r"""`search` returns the best matches for a query vector. An empty store returns no results."""),
        (43, 43, r"""**The core of retrieval.** `matrix @ query` is a matrix-vector product: an `(n, d)` matrix times a `(d,)` vector gives `(n,)`, one dot product per stored chunk, computed in a single fast operation. Because all vectors have length 1, each dot product is the cosine similarity."""),
        (44, 44, r"""`np.argsort(-scores)` sorts indices from highest to lowest score (negating flips ascending order); `[:top_k]` keeps the best few. Sorting everything is O(n log n): fine for thousands of chunks; for millions you would use an approximate nearest-neighbour index (FAISS, HNSW, pgvector, Azure AI Search)."""),
        (45, 45, r"""Build the result objects, dropping anything below `min_score` (the threshold that lets the system say "not found"). `float(...)` converts NumPy's float32 into a normal Python float so it can be turned into JSON."""),
        (47, 51, r"""`sources` counts chunks per file, using the `counts.get(key, 0) + 1` idiom. It powers `GET /documents` and the CLI `stats` command."""),
        (53, 54, r"""`save` persists the index. `mkdir(parents=True, exist_ok=True)` creates the folder if needed and does not complain if it exists."""),
        (55, 58, r"""If the store is empty, delete any stale `vectors.npy` (so a later `load` cannot read outdated data); otherwise write the matrix in NumPy's binary `.npy` format (fast and exact)."""),
        (59, 61, r"""Save the chunk texts and metadata as JSON (`asdict` turns each dataclass into a dict). **Limitation:** the two files are not written atomically; a crash between them could leave them out of sync. A production system would write to a temp file and rename it, or use a real database."""),
        (63, 64, r"""`@classmethod` `load` is an alternative constructor: `VectorStore.load(path)` returns a populated store."""),
        (65, 68, r"""Create an empty store. If no index file exists yet (first run), return that empty store instead of raising an error."""),
        (69, 69, r"""Read the JSON and rebuild each `Chunk` from its dictionary (`Chunk(**item)` unpacks the dict into keyword arguments)."""),
        (70, 72, r"""If there are chunks, load the matrix and reuse `add` (which re-validates the invariant), then return the store."""),
    ],
)

APP["app/llm.py"] = (
    r"""The generation step ("G" in RAG): turn the retrieved chunks and the user's question into a prompt, call Claude, return the answer.
Also contains an offline fallback so the whole project runs without an API key.""",
    [
        (1, 1, r"""Docstring."""),
        (2, 3, r"""`os` to check for the API key; `Protocol` for the interface."""),
        (5, 5, r"""The official Anthropic SDK (`pip install anthropic`). We use the SDK, never hand-rolled HTTP."""),
        (7, 8, r"""Project types we depend on: `Settings` and `SearchResult`."""),
        (10, 10, r"""The exact "I don't know" sentence lives in **one** constant. It is used inside the model's instructions *and* returned directly by the pipeline when nothing relevant is found, so behaviour is consistent."""),
        (12, 17, r"""**The system prompt: the most important 6 lines for answer quality.** It is an f-string so it can embed the constant above. Rule 1 says use *only* the supplied context (this is what "grounding" means; it reduces hallucination but is not a guarantee) and gives the model an explicit, exact escape hatch when the answer is absent. Rule 2 forces numbered citations such as `[1]` that match the numbered passages in the user message. Rule 3 keeps answers short. The system prompt never changes between requests, which also makes it eligible for prompt caching if it grows."""),
        (24, 25, r"""The `LLM` interface: any object with `generate(question, results) -> str`. The real model, the offline fallback and the test fake all satisfy it."""),
        (28, 28, r"""`build_user_message` formats the retrieved chunks and the question into the text sent as the user turn."""),
        (29, 32, r"""A generator expression numbers each passage starting at 1 (`enumerate(..., start=1)`, because humans and models say "passage 1", not "passage 0") and prints `[n] (source: file)` followed by the chunk text. `"\n\n".join(...)` puts a blank line between passages."""),
        (33, 33, r"""Wrap the passages in `<context>` tags, then put the question **after** the context. Clear delimiters help the model separate reference material from the question (and are a first step against prompt injection hidden in documents; they reduce, not eliminate, that risk). Putting the question last is recommended practice for long contexts."""),
        (36, 40, r"""`ClaudeLLM` remembers the model name and token limit. Note `_client` starts as `None`: the client is created **lazily**, so the app can start, pass health checks and accept uploads even with no API key. A missing key only surfaces when someone asks a question."""),
        (42, 44, r"""On the first call create the client. `anthropic.Anthropic()` with no arguments reads credentials from the environment (`ANTHROPIC_API_KEY`); the key is never written in code."""),
        (20, 21, r"""`MissingCredentialsError` is our own small exception class. It exists because the Anthropic SDK reports "no API key" as a bare `TypeError` with a cryptic message; wrapping it in a named exception lets the API and CLI show a clear, actionable error (see the `except` block below)."""),
        (45, 52, r"""**The API call.** `model` and `max_tokens` come from config. `system=` carries the fixed instructions. `messages=` holds a single user turn built by `build_user_message`. `output_config={"effort": "medium"}` sets how much the model reasons (a cost/latency dial; Claude Opus 5 also decides adaptively when to think). We deliberately do **not** send `temperature`: current models reject sampling parameters. The whole call sits inside a `try` so a missing key can be translated (next block)."""),
        (53, 56, r"""**Turning a cryptic SDK error into a clear one.** With no credentials, the SDK raises `TypeError("Could not resolve authentication method...")` at request time. Without this block that would surface as an unexplained crash or an HTTP 500 with a traceback. We check the message for the phrase `authentication method`, and if it matches, raise `MissingCredentialsError("...Set ANTHROPIC_API_KEY.")` (`from exc` keeps the original attached for debugging). Any *other* `TypeError` is re-raised untouched with a bare `raise`, so real programming bugs are never hidden. **Trade-off:** matching on message text is brittle if the SDK rewords it; the SDK offers no dedicated exception for this case, and a test pins the behaviour."""),
        (57, 58, r"""If the model's safety systems declined (`stop_reason == "refusal"`), the reply may be empty, so return a safe message instead of crashing. Always check `stop_reason` before trusting `content`."""),
        (59, 59, r"""`response.content` is a *list of blocks* (thinking blocks, text blocks, ...). We keep only blocks whose `type` is `"text"` and join their `.text`. Checking the type first avoids attribute errors on non-text blocks."""),
        (62, 66, r"""`ExtractiveLLM` is a zero-cost offline fallback: no model, it simply returns the best-matching chunk verbatim plus a `[1]` citation. It proves retrieval works on its own, lets the demo run with no key, and makes CI cheap."""),
        (69, 70, r"""`build_llm` is a small **factory function**: it decides which implementation to use, based on config."""),
        (71, 72, r"""In `auto` mode, use Claude if `ANTHROPIC_API_KEY` is set, otherwise the extractive fallback. (If you authenticate another way, for example `ant auth login`, set `LLM_PROVIDER=claude` explicitly.)"""),
        (73, 76, r"""Explicit choices: return the matching implementation."""),
        (77, 77, r"""Any other value is a configuration error: fail immediately and loudly at start-up, not silently later."""),
    ],
)

APP["app/rag.py"] = (
    r"""The orchestrator. This is the file that *is* the RAG pipeline: it wires loader, chunker, embedder, vector store and LLM together
in two flows: **ingest** (index documents) and **ask** (retrieve, then generate).""",
    [
        (1, 1, r"""Docstring."""),
        (2, 3, r"""`dataclass` and `Path`."""),
        (5, 10, r"""Imports of every collaborator. Note it imports the *interfaces* `Embedder` and `LLM`, not just concrete classes: the pipeline depends on abstractions."""),
        (13, 18, r"""`Citation`: one piece of evidence shown to the user: which file, which chunk, how similar (`score`), and the chunk text."""),
        (21, 25, r"""`Answer`: the pipeline's result: the answer text; `grounded` (True only if retrieval found evidence and the LLM was consulted; False for "no documents" and "nothing relevant"); and the list of citations."""),
        (28, 28, r"""The pipeline class."""),
        (29, 33, r"""**Dependency injection**: the constructor *receives* its embedder, store, LLM and settings instead of creating them. In production `build_pipeline` (bottom of file) passes real ones; in tests we pass fakes. This is why 36 tests run in half a second with no network."""),
        (35, 36, r"""`ingest` indexes documents and returns a count summary. `total_chunks` counts how many chunks were created."""),
        (37, 38, r"""For each document, first **remove any existing chunks with the same source**. This makes ingest a *replace* (idempotent), so uploading the same file twice never duplicates content. **Limitation:** if a later step fails, the old version is already gone."""),
        (39, 41, r"""Split into chunks using the configured size and overlap. A document with no text yields no chunks; skip it."""),
        (42, 42, r"""Embed **all** of the document's chunks in one batched call: much faster than one at a time."""),
        (43, 44, r"""Store the chunks with their vectors, and update the running total."""),
        (45, 46, r"""After all documents, persist the index to disk once (not once per document) and return the summary."""),
        (48, 48, r"""`ask` is the query flow."""),
        (49, 50, r"""**Guard 1:** an empty index has nothing to search; say so, and do not call the model."""),
        (51, 51, r"""Embed the question with the *query* encoder, giving one vector."""),
        (52, 52, r"""**Retrieval:** find the `top_k` most similar chunks that score at least `min_score`."""),
        (53, 54, r"""**Guard 2 (important):** if nothing is similar enough, return "not found" **without calling the LLM**. It is cheaper and faster, and it removes any chance of the model inventing an answer for an off-topic question."""),
        (55, 55, r"""**Generation:** the LLM receives only the question and the retrieved chunks, not the whole corpus."""),
        (56, 58, r"""Build the citation list from the same results the model saw, so what the user is shown is exactly the evidence used. Scores are rounded to 4 decimal places."""),
        (59, 59, r"""Return the answer, marked `grounded=True`."""),
        (61, 63, r"""`seed_if_empty` indexes a folder of documents **only if the index has nothing in it yet** (and the folder exists). It is what lets a stateless deployment start with useful content: an ephemeral serverless instance boots with an empty index every time, so it loads the bundled sample documents once. Calling it again later does nothing, because the index is no longer empty. It reuses `ingest`, so it is chunked, embedded and saved the same way."""),
        (66, 72, r"""`build_pipeline` is the **composition root**: the one place where concrete classes are chosen and connected. It builds the real embedder (passing the model cache folder from settings), loads any previously saved index from disk (so restarts do not lose data), creates the LLM from settings, and assembles the pipeline. If a `seed_dir` is configured (it is on Vercel), it then seeds the empty index from that folder before returning the ready pipeline."""),
    ],
)

APP["app/api.py"] = (
    r"""The HTTP layer (FastAPI). It contains no RAG logic: it validates input, calls the pipeline, and translates results and errors into HTTP responses.""",
    [
        (1, 1, r"""Docstring: "thin" wrapper means business logic stays in `rag.py`."""),
        (2, 4, r"""`asdict` converts dataclasses to dicts; `lru_cache` memoises a function; `Path` for file names."""),
        (6, 6, r"""The Anthropic SDK is imported here only for its **typed exception classes**, used in `/ask` for error mapping."""),
        (7, 9, r"""FastAPI building blocks (`Depends` = dependency injection, `File`/`UploadFile` = multipart uploads, `HTTPException` = error responses), pydantic (`BaseModel`, `Field` = request/response validation), and `PdfReadError` for corrupt PDFs."""),
        (11, 14, r"""Project imports: settings, our `MissingCredentialsError` (used to give a clear message when no Claude key is set), loader helpers, and the pipeline plus its builder."""),
        (16, 16, r"""Upload size cap: 5 MB. Without a limit, one huge upload could exhaust memory."""),
        (18, 18, r"""Create the app. FastAPI automatically serves interactive docs at `/docs` (Swagger UI) and a machine-readable schema at `/openapi.json`."""),
        (21, 23, r"""`get_pipeline` builds the pipeline **once**: `@lru_cache` remembers the result, so every request shares one instance (a singleton). It is expensive (loads the embedding model and the index), so the first request pays a cold start. Endpoints obtain it via `Depends(get_pipeline)`, which is also how tests swap in a fake pipeline (`app.dependency_overrides`)."""),
        (26, 27, r"""`AskRequest` is the request body schema. `Field(min_length=1, max_length=2000)` makes pydantic reject empty or oversized questions automatically with HTTP 422, before our code runs."""),
        (30, 34, r"""`CitationOut`: the JSON shape of one citation."""),
        (37, 40, r"""`AskResponse`: the JSON shape of an answer. Declared as `response_model` below so responses are validated, filtered to these fields, and documented in `/docs`."""),
        (43, 45, r"""`GET /health` returns `{"status": "ok"}`. It deliberately does **not** depend on the pipeline, so it is instant and does not force the model to load. Container platforms poll this to decide whether the service is alive."""),
        (48, 50, r"""`GET /documents` lists what is indexed: source file name and chunk count."""),
        (53, 56, r"""`POST /documents` uploads a file (multipart form data); `status_code=201` means "Created". Note `def`, **not** `async def`: FastAPI runs plain functions in a worker thread pool, so slow blocking work (embedding, network calls) does not freeze the server's event loop for other users."""),
        (57, 57, r"""Sanitise the uploaded file name down to its last component."""),
        (58, 59, r"""Whitelist the extension. Anything else is HTTP **415 Unsupported Media Type**."""),
        (60, 60, r"""Read at most `MAX_UPLOAD_BYTES + 1` bytes. The extra byte is a trick: if we get more than the limit, the file is too big, and we know it without ever loading a huge file into memory."""),
        (61, 62, r"""Too big: HTTP **413 Payload Too Large**."""),
        (63, 66, r"""Try to parse the file. `ValueError` (unsupported type) and `PdfReadError` (corrupt PDF) become HTTP **422 Unprocessable Content**. `from exc` keeps the original error attached for debugging."""),
        (67, 68, r"""A file with no extractable text (for example a scanned PDF) is rejected with 422 rather than silently indexed as nothing."""),
        (69, 69, r"""Ingest it and return the counts (`{"documents": 1, "chunks": n}`)."""),
        (72, 73, r"""`POST /ask` takes an `AskRequest` (already validated), returns an `AskResponse`."""),
        (74, 75, r"""Call the pipeline. `asdict` recursively converts the `Answer` dataclass and its nested `Citation` objects into plain dictionaries for JSON."""),
        (76, 77, r"""No Claude credentials configured (raised by `llm.py`): return **500** with a message that tells the operator exactly what to fix (`set ANTHROPIC_API_KEY`). It is listed first because it is our own exception and the most common first-run problem."""),
        (78, 79, r"""Claude rate limit (HTTP 429 from Anthropic) becomes HTTP **429** for our client, who can retry later."""),
        (80, 81, r"""Bad or missing API key is *our* configuration problem, not the caller's: return **500** with a generic message (no details leaked)."""),
        (82, 83, r"""Network failure reaching Anthropic: HTTP **503 Service Unavailable**."""),
        (84, 85, r"""Any other error status from Anthropic: HTTP **502 Bad Gateway** (an upstream service failed). **Order matters:** `RateLimitError` and `AuthenticationError` are *subclasses* of `APIStatusError`, so the specific handlers must come before this general one, otherwise they would never run."""),
    ],
)

APP["app/cli.py"] = (
    r"""A command-line front end for the same pipeline: useful for scripting, demos and debugging without running a server.""",
    [
        (1, 1, r"""Docstring."""),
        (2, 4, r"""`argparse` (standard library command-line parser), `sys` (needed for the path fix below) and `Path`."""),
        (6, 7, r"""**Makes the file runnable from VS Code's "Run Python File" button.** When you run `python app/cli.py` directly, `__package__` is empty and Python puts the `app/` folder (not the project root) on `sys.path`, so `from app.config import ...` fails with `ModuleNotFoundError: No module named 'app'`. When run the normal way (`python -m app.cli`) `__package__` is set and this block is skipped. Otherwise we insert the project root (`Path(__file__).resolve().parent.parent`) at the front of the import path."""),
        (9, 12, r"""Reuse the same settings, error type, folder loader and pipeline builder as the API: **one pipeline, two front ends**. The `# noqa: E402` comments silence the linter warning "import not at top of file", which is intentional here because the path fix must run first."""),
        (15, 15, r"""`main` accepts an optional argument list. Passing `None` makes argparse read `sys.argv`; tests can pass their own list."""),
        (16, 17, r"""Create the parser (`prog` sets the name shown in help). `add_subparsers` creates the `ingest` / `ask` / `stats` sub-commands; `required=True` forces the user to pick one."""),
        (18, 19, r"""`ingest <directory>`: `type=Path` converts the text argument into a `Path`."""),
        (20, 21, r"""`ask "<question>"`."""),
        (22, 22, r"""`stats` takes no arguments."""),
        (23, 23, r"""Parse the command line into `args`. Bad input prints usage and exits."""),
        (25, 25, r"""Build the real pipeline (loads the embedding model and any saved index)."""),
        (26, 27, r"""`ingest`: read every supported file in the folder, index it, print the counts."""),
        (28, 29, r"""`stats`: print the source files and their chunk counts."""),
        (30, 34, r"""Otherwise it is `ask`. The call is wrapped so that a missing API key produces a one-line, actionable message (`SystemExit("error: ...")` exits with a non-zero status and prints just that text) instead of a stack trace, and it suggests the offline alternative."""),
        (35, 37, r"""Print the answer, then one line per citation with file, chunk number and similarity score."""),
        (40, 41, r"""Standard guard so `python -m app.cli ...` runs `main()`, but importing the module does not."""),
    ],
)

# ---------------------------------------------------------------------------------------------
# Supporting files: annotated by top-level name ("@header" = the imports/constants at the top).
# ---------------------------------------------------------------------------------------------
BY_NAME = {}

BY_NAME["eval/run_eval.py"] = (
    r"""Retrieval evaluation: measures whether the *retrieval* half of the system works, with no LLM calls and therefore no cost.
The single most useful habit in RAG work: measure retrieval separately from generation.""",
    {
        "@header": r"""Imports, `ROOT` (the project folder, found relative to this file so the script works from any directory) and the same path fix as `cli.py`, so the file also runs from VS Code's "Run Python File" button (`__package__` is empty only when launched as a plain file).""",
        "@main-guard": r"""Runs `main()` only when the file is executed directly (`python -m eval.run_eval`), not when imported.""",
        "main": r"""Builds a throw-away in-memory index of `data/sample_docs`, then runs every question in `eval/qa_pairs.json`. **Answerable** questions name the document that should contain the answer; the metric is **hit@k** (was the right document among the top-k results?) and **MRR** (mean reciprocal rank: 1 if the right document is first, 0.5 if second, and so on). **Unanswerable** questions (`expected_source` is `null`) must be *refused* at `MIN_SCORE`: that is what proves the threshold works. Current result: hit@4 = 12/12, MRR = 0.958, refused 5/5.""",
    },
)

BY_NAME["tests/conftest.py"] = (
    r"""Shared test fixtures. Tests use **fakes**, so they need no model download, no network and no API key, and run in well under a second.""",
    {
        "@header": r"""Imports, and `DIM = 512`, the size of the fake vectors.""",
        "FakeEmbedder": r"""A deterministic stand-in for the real embedder. It hashes every word to one of 512 slots and counts occurrences ("bag of words"), then normalises. Texts that share words get similar vectors, so retrieval behaves sensibly enough to test logic. It satisfies the same `Embedder` interface as the real class.""",
        "FakeLLM": r"""Records every call it receives and returns a fixed string. Tests can assert *whether* the LLM was called (for example, that it is **not** called for off-topic questions).""",
        "settings": r"""Fixture: small chunk size (300) and a low `min_score` (0.2, suited to the crude fake embeddings), with the index saved to pytest's temporary folder so tests never touch real data.""",
        "fake_llm": r"""Fixture: a fresh `FakeLLM` per test.""",
        "pipeline": r"""Fixture: a real `RagPipeline` assembled from fakes. Possible only because of dependency injection.""",
    },
)

BY_NAME["tests/test_chunker.py"] = (
    r"""Unit tests for chunking.""",
    {
        "@header": r"""Imports.""",
        "test_short_text_is_a_single_chunk": r"""Text shorter than `size` must come back unchanged as one chunk.""",
        "test_empty_text_gives_no_chunks": r"""Whitespace-only input produces no chunks (edge case).""",
        "test_no_chunk_exceeds_size": r"""The key invariant: no chunk is ever longer than `size`, across ten paragraphs.""",
        "test_overlap_repeats_the_end_of_the_previous_chunk": r"""The last words of chunk 0 must appear in chunk 1: proves overlap works.""",
        "test_oversized_sentence_is_hard_split": r"""A 450-character string with no spaces is cut into three pieces of at most 200.""",
        "test_overlap_must_be_smaller_than_size": r"""`pytest.raises` asserts the guard clause raises `ValueError`.""",
        "test_chunk_document_numbers_chunks_and_keeps_source": r"""Chunks are numbered 0, 1, 2, ... and carry the file name (needed for citations).""",
    },
)

BY_NAME["tests/test_vector_store.py"] = (
    r"""Unit tests for the vector store, using tiny hand-made 3-dimensional vectors so results are easy to verify by hand.""",
    {
        "@header": r"""Imports.""",
        "make_store": r"""Helper: three chunks with known vectors. `[0.6, 0.8, 0]` is deliberately 60% similar to `[1, 0, 0]`.""",
        "test_search_returns_best_match_first": r"""Querying `[1,0,0]` must rank alpha (score 1.0), gamma (0.6), beta (0.0).""",
        "test_min_score_filters_weak_matches": r"""With a 0.5 threshold, beta (0.0) is excluded.""",
        "test_top_k_limits_results": r"""`top_k=1` returns exactly one result.""",
        "test_remove_source_drops_only_that_source": r"""Removing `a.md` leaves only `b.md`'s single chunk.""",
        "test_empty_store_returns_nothing": r"""Searching an empty store returns `[]` instead of crashing.""",
        "test_add_rejects_mismatched_lengths": r"""One chunk with two vectors must raise `ValueError` (invariant guard).""",
        "test_save_and_load_round_trip": r"""Save to disk, load, and confirm the same sources and identical search results: proves persistence.""",
    },
)

BY_NAME["tests/test_rag.py"] = (
    r"""Tests of the pipeline's behaviour: what it does at each decision point.""",
    {
        "@header": r"""Imports and two tiny sample documents.""",
        "test_ask_on_empty_index_does_not_call_llm": r"""Guard 1: an empty index returns `grounded=False`, no citations, and the LLM is never called.""",
        "test_ask_retrieves_the_relevant_document_and_cites_it": r"""The happy path: the leave question retrieves `leave.md` first, the fake LLM is called exactly once, and the answer is marked grounded.""",
        "test_irrelevant_question_short_circuits_without_calling_llm": r"""Guard 2: nonsense input returns the not-found message and the LLM is **not** called.""",
        "test_reingesting_a_source_replaces_instead_of_duplicating": r"""Ingest the same file twice: chunk counts stay the same.""",
        "test_ingest_persists_the_index_to_disk": r"""After ingest, `chunks.json` and `vectors.npy` exist.""",
        "test_prompt_numbers_passages_and_includes_the_question": r"""The prompt contains `[1] (source: leave.md)` and ends with the question.""",
        "test_seed_if_empty_indexes_a_folder_only_when_the_index_is_empty": r"""Seeds from a temporary folder; adding another file and calling `seed_if_empty` again must change nothing, because the index is no longer empty.""",
        "test_seed_if_empty_ignores_a_missing_folder": r"""A folder that does not exist is silently ignored, so a mis-set `SEED_DIR` cannot crash start-up.""",
    },
)

BY_NAME["tests/test_llm.py"] = (
    r"""Tests for the generation layer, using a stub client so no real API call is made.""",
    {
        "@header": r"""Imports and a shared `RESULTS` list (one retrieved chunk).""",
        "StubClient": r"""Imitates `anthropic.Anthropic`: it exposes `messages.create(...)`, records the arguments it was called with, and returns a canned response (or raises it, if the canned value is an exception).""",
        "claude_with": r"""Helper: builds a `ClaudeLLM` and injects the stub client (possible because the client is a replaceable attribute).""",
        "test_claude_request_is_grounded_and_text_blocks_are_joined": r"""Checks the request sent to Claude (model, `max_tokens`, system prompt, numbered passage in the user message) and that only `text` blocks are returned, ignoring a `thinking` block.""",
        "test_claude_refusal_stop_reason_returns_a_safe_message": r"""A `refusal` stop reason yields a safe message rather than an error.""",
        "test_extractive_llm_returns_top_passage_with_citation": r"""The offline fallback returns the top chunk plus `[1]`.""",
        "test_auto_provider_uses_extractive_without_api_key": r"""`monkeypatch.delenv` removes the key: auto mode must choose the extractive fallback.""",
        "test_auto_provider_uses_claude_with_api_key": r"""With a (fake) key set, auto mode must choose `ClaudeLLM`.""",
        "test_unknown_provider_is_rejected": r"""A misspelt provider fails fast with `ValueError`.""",
        "test_missing_api_key_becomes_a_clear_error": r"""Feeds the stub the exact `TypeError` the real SDK raises when no key is set (observed by running the real SDK with no credentials) and asserts we convert it to `MissingCredentialsError` mentioning `ANTHROPIC_API_KEY`.""",
        "test_unrelated_type_errors_are_not_swallowed": r"""The counter-test: a *different* `TypeError` must pass through unchanged, proving the `except` block does not hide genuine bugs.""",
    },
)

BY_NAME["tests/test_api.py"] = (
    r"""HTTP-level tests using FastAPI's `TestClient`, which calls the app in-process (no server, no network).""",
    {
        "@header": r"""Imports, including `anthropic` and `httpx` to build a realistic 429 error.""",
        "client": r"""Fixture: overrides the `get_pipeline` dependency with the test pipeline (fakes), then clears the override afterwards.""",
        "test_health": r"""`/health` returns `{"status": "ok"}`.""",
        "test_upload_then_ask_returns_cited_answer": r"""End-to-end through HTTP: upload a file (201, one chunk), list documents, ask a question, and check the answer is grounded and cites `leave.md`.""",
        "test_unsupported_file_type_is_rejected": r"""An `.exe` upload returns 415.""",
        "test_empty_file_is_rejected": r"""A whitespace-only file returns 422.""",
        "test_oversized_file_is_rejected": r"""A file one byte over 5 MB returns 413.""",
        "test_empty_question_fails_validation": r"""An empty question returns 422 from pydantic validation.""",
        "test_rate_limit_from_model_maps_to_429": r"""Simulates Anthropic returning 429: our API must return 429 too (proves the error-mapping chain).""",
        "test_missing_credentials_maps_to_500_with_a_helpful_message": r"""When the pipeline raises `MissingCredentialsError`, the API returns 500 and the response body mentions `ANTHROPIC_API_KEY`, so an operator knows what to fix.""",
    },
)

DOCKERFILE = (
    r"""The container recipe. Docker is not installed on the machine this was built on, so **this file has not been build-tested**; it follows standard patterns and should be verified with `docker build` before you rely on it.""",
    [
        (1, 1, r"""Start from a small official Python 3.12 image (`slim` = fewer packages, smaller attack surface)."""),
        (3, 4, r"""Environment variables: no `.pyc` clutter, unbuffered logs (so `docker logs` shows output immediately), the embedding-model cache location, and where the index is stored (`/data/index`, intended to be a mounted volume so data survives restarts)."""),
        (6, 6, r"""Working directory inside the container."""),
        (7, 8, r"""Copy **only** `requirements.txt` first and install. Docker caches layers, so dependencies are re-installed only when this file changes, not on every code edit (a standard build-speed trick)."""),
        (10, 11, r"""Download the embedding model **during the build** and bake it into the image, so containers start fast and work without internet access."""),
        (13, 14, r"""Now copy the application code and the sample data (after the slow steps, so code edits are cheap to rebuild)."""),
        (16, 17, r"""Create an unprivileged user, give it the folders it must write to, and switch to it. Never run application containers as root."""),
        (19, 19, r"""Documents the port the service listens on."""),
        (20, 20, r"""Container health check: Docker/Azure periodically call `/health` to decide whether the container is healthy."""),
        (21, 21, r"""Start the API with uvicorn, listening on all interfaces so traffic from outside the container can reach it."""),
    ],
)


def fence(lines, start, end):
    width = len(str(end))
    body = "\n".join(f"{n:>{width}} | {lines[n - 1]}" for n in range(start, end + 1))
    return f"```python\n{body}\n```"


def render_ranges(path, intro, segments, lang="python"):
    text = (ROOT / path).read_text(encoding="utf-8")
    lines = text.splitlines()
    covered = set()
    for a, b, _ in segments:
        assert 1 <= a <= b <= len(lines), f"{path}: bad range {a}-{b} (file has {len(lines)} lines)"
        for n in range(a, b + 1):
            assert n not in covered, f"{path}: line {n} annotated twice"
            covered.add(n)
    missing = [n for n, line in enumerate(lines, 1) if line.strip() and n not in covered]
    assert not missing, f"{path}: undocumented lines {missing}"

    out = [f"## `{path}`\n", intro.strip() + "\n"]
    for a, b, note in sorted(segments):
        label = f"L{a}" if a == b else f"L{a}-{b}"
        code = fence(lines, a, b).replace("```python", f"```{lang}", 1)
        out.append(f"**{label}**\n\n{code}\n\n{note.strip()}\n")
    return "\n".join(out)


def render_by_name(path, intro, notes):
    text = (ROOT / path).read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text)
    segments, header = [], None
    for node in tree.body:
        is_def = isinstance(node, (ast.FunctionDef, ast.ClassDef))
        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        if isinstance(node, ast.If) and "__name__" in ast.unparse(node.test):
            segments.append(("@main-guard", start, node.end_lineno))
        elif is_def:
            segments.append((node.name, start, node.end_lineno))
        elif header is None:
            header = [start, node.end_lineno]
        else:
            assert header[1] >= start - 3, f"{path}: non-def code after a definition at line {start}"
            header[1] = node.end_lineno
    if header:
        segments.insert(0, ("@header", header[0], header[1]))
    names = [s[0] for s in segments]
    assert set(names) == set(notes), f"{path}: notes mismatch. missing={set(names) - set(notes)} extra={set(notes) - set(names)}"

    out = [f"## `{path}`\n", intro.strip() + "\n"]
    for name, a, b in segments:
        label = {"@header": "header", "@main-guard": "entry point"}.get(name, f"`{name}`")
        out.append(f"**{label}** (L{a}-{b})\n\n{fence(lines, a, b)}\n\n{notes[name].strip()}\n")
    return "\n".join(out)


def main():
    parts = [
        "# Code Walkthrough: every line explained\n",
        "> Generated by `scripts/build_walkthrough.py` from the real source files: the code shown here is exactly what is in the repository, "
        "with real line numbers. The script fails if any line is left unexplained.\n",
        "**How to read this:** follow the files in the order below; it is the order data flows through the system. "
        "Read `docs/ARCHITECTURE.md` first if you want the big picture, then come here for the detail.\n",
        "## The map\n",
        "```mermaid\nflowchart LR\n  cfg[config.py] --> rag\n  loader[loader.py<br/>bytes -> Document] --> chunker[chunker.py<br/>Document -> Chunks]\n"
        "  chunker --> rag[rag.py<br/>RagPipeline]\n  emb[embeddings.py<br/>text -> vector] --> rag\n  vs[vector_store.py<br/>similarity search] --> rag\n"
        "  llm[llm.py<br/>prompt + Claude] --> rag\n  rag --> api[api.py<br/>FastAPI]\n  rag --> cli[cli.py<br/>command line]\n```\n",
        "| Step | File | One-line job |\n|---|---|---|\n"
        "| 0 | `config.py` | All tunable settings from environment variables |\n"
        "| 1 | `loader.py` | Read `.txt`/`.md`/`.pdf` into plain text |\n"
        "| 2 | `chunker.py` | Split text into overlapping chunks |\n"
        "| 3 | `embeddings.py` | Turn text into meaning-vectors |\n"
        "| 4 | `vector_store.py` | Store vectors, find the nearest ones |\n"
        "| 5 | `llm.py` | Build the grounded prompt, call Claude |\n"
        "| 6 | `rag.py` | Orchestrate ingest and ask |\n"
        "| 7 | `api.py`, `cli.py` | Expose it over HTTP and the command line |\n",
        "Files are shown in that order, then the eval script, the tests and the Dockerfile.\n",
        "---\n",
    ]
    order = ["config", "loader", "chunker", "embeddings", "vector_store", "llm", "rag", "api", "cli"]
    for name in order:
        path = f"app/{name}.py"
        intro, segs = APP[path]
        parts.append(render_ranges(path, intro, segs))
        parts.append("\n---\n")
    for path in ["eval/run_eval.py", "tests/conftest.py", "tests/test_chunker.py", "tests/test_vector_store.py",
                 "tests/test_rag.py", "tests/test_llm.py", "tests/test_api.py"]:
        intro, notes = BY_NAME[path]
        parts.append(render_by_name(path, intro, notes))
        parts.append("\n---\n")
    intro, segs = DOCKERFILE
    parts.append(render_ranges("Dockerfile", intro, segs, lang="dockerfile"))
    OUT.write_text("\n".join(parts), encoding="utf-8")
    total = sum(len((ROOT / f"app/{n}.py").read_text(encoding="utf-8").splitlines()) for n in order)
    print(f"wrote {OUT.relative_to(ROOT)}: {total} application lines documented, all non-blank lines covered")


if __name__ == "__main__":
    main()
