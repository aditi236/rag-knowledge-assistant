"""Split documents into overlapping, size-bounded chunks that respect paragraph and sentence edges."""
import re
from dataclasses import dataclass

from app.loader import Document


@dataclass(frozen=True)
class Chunk:
    source: str
    index: int
    text: str


def _split_units(text: str, size: int) -> list[str]:
    units = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= size:
            units.append(paragraph)
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            while len(sentence) > size:
                units.append(sentence[:size])
                sentence = sentence[size:]
            if sentence:
                units.append(sentence)
    return units


def _overlap_tail(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    tail = text[-overlap:]
    first_space = tail.find(" ")
    return tail[first_space + 1:] if first_space != -1 else tail


def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    chunks: list[str] = []
    current = ""
    for unit in _split_units(text, size):
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= size:
            current = candidate
            continue
        chunks.append(current)
        tail = _overlap_tail(current, overlap)
        joined = f"{tail}\n\n{unit}" if tail else unit
        current = joined if len(joined) <= size else unit
    if current:
        chunks.append(current)
    return chunks


def chunk_document(document: Document, size: int, overlap: int) -> list[Chunk]:
    pieces = chunk_text(document.text, size, overlap)
    return [Chunk(source=document.source, index=i, text=piece) for i, piece in enumerate(pieces)]
