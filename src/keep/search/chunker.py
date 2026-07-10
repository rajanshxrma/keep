"""Text extraction + chunking for local files.

The sliding-window chunk_text() logic is lifted directly from finance-rag's
own chunker.py (same author, same approach: proven, simple, no reason to
reinvent it) -- extended here to handle plain text/markdown directly in
addition to PDFs, since "your own files" covers more than bank statements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


@dataclass
class Chunk:
    text: str
    page: int
    index: int
    source_file: str
    metadata: dict = field(default_factory=dict)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Sliding window chunker with overlap -- unchanged from finance-rag's version."""
    if not text or not text.strip():
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def _extract_pdf_pages(file_path: Path) -> list[dict]:
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                pages.append({"page": i + 1, "text": text})
    return pages


def chunk_file(file_path: str | Path, chunk_size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Full pipeline: file -> (page-aware for PDFs, single-page otherwise) -> chunks."""
    file_path = Path(file_path)
    source_name = str(file_path)

    if file_path.suffix.lower() == ".pdf":
        pages = _extract_pdf_pages(file_path)
    elif file_path.suffix.lower() in (".txt", ".md"):
        text = file_path.read_text(errors="ignore")
        pages = [{"page": 1, "text": text}] if text.strip() else []
    else:
        raise ValueError(
            f"Unsupported file type '{file_path.suffix}' -- keep currently handles "
            f"{sorted(SUPPORTED_EXTENSIONS)}."
        )

    all_chunks = []
    chunk_index = 0
    for page_data in pages:
        for text in chunk_text(page_data["text"], chunk_size, overlap):
            all_chunks.append(
                Chunk(text=text, page=page_data["page"], index=chunk_index, source_file=source_name)
            )
            chunk_index += 1

    return all_chunks
