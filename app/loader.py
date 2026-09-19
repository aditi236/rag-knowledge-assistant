"""Turn files on disk (or uploaded bytes) into plain-text Document objects."""
import io
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


@dataclass(frozen=True)
class Document:
    source: str
    text: str


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in {".txt", ".md"}:
        return data.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {suffix or filename}")


def load_bytes(filename: str, data: bytes) -> Document:
    return Document(source=Path(filename).name, text=extract_text(filename, data))


def load_directory(directory: Path) -> list[Document]:
    documents = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            documents.append(load_bytes(path.name, path.read_bytes()))
    return documents
