"""Runtime configuration, read once from environment variables (12-factor style)."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    index_dir: Path = Path(os.getenv("INDEX_DIR", "storage/index"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    llm_provider: str = os.getenv("LLM_PROVIDER", "auto")
    llm_model: str = os.getenv("LLM_MODEL", "claude-opus-5")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    top_k: int = int(os.getenv("TOP_K", "4"))
    min_score: float = float(os.getenv("MIN_SCORE", "0.58"))
    max_answer_tokens: int = int(os.getenv("MAX_ANSWER_TOKENS", "4096"))
