"""HTTP layer: a thin FastAPI wrapper around the RagPipeline."""
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

import anthropic
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from pypdf.errors import PdfReadError

from app.config import Settings
from app.loader import SUPPORTED_EXTENSIONS, load_bytes
from app.rag import RagPipeline, build_pipeline

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

app = FastAPI(title="RAG Knowledge Assistant", version="1.0.0")


@lru_cache
def get_pipeline() -> RagPipeline:
    return build_pipeline(Settings())


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class CitationOut(BaseModel):
    source: str
    chunk_index: int
    score: float
    text: str


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    citations: list[CitationOut]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/documents")
def list_documents(pipeline: RagPipeline = Depends(get_pipeline)) -> dict[str, int]:
    return pipeline.store.sources()


@app.post("/documents", status_code=201)
def upload_document(
    file: UploadFile = File(...), pipeline: RagPipeline = Depends(get_pipeline)
) -> dict[str, int]:
    name = Path(file.filename or "").name
    if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(415, f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")
    try:
        document = load_bytes(name, data)
    except (ValueError, PdfReadError) as exc:
        raise HTTPException(422, f"Could not read file: {exc}") from exc
    if not document.text.strip():
        raise HTTPException(422, "File contains no extractable text")
    return pipeline.ingest([document])


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, pipeline: RagPipeline = Depends(get_pipeline)) -> dict:
    try:
        return asdict(pipeline.ask(request.question))
    except anthropic.RateLimitError as exc:
        raise HTTPException(429, "Model rate limit reached, retry shortly") from exc
    except anthropic.AuthenticationError as exc:
        raise HTTPException(500, "Server is missing valid model credentials") from exc
    except anthropic.APIConnectionError as exc:
        raise HTTPException(503, "Could not reach the model API") from exc
    except anthropic.APIStatusError as exc:
        raise HTTPException(502, "The model API returned an error") from exc
