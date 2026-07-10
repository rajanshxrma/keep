"""Ingest pipeline: discover files -> chunk -> embed -> store in the local index."""

from __future__ import annotations

from pathlib import Path

from keep.search.chunker import SUPPORTED_EXTENSIONS, chunk_file
from keep.search.index import Index


def discover_files(path: str | Path) -> list[Path]:
    """A single supported file, or every supported file under a directory
    (recursive). Unsupported files are silently skipped, not errored on --
    pointing keep at ~/Documents shouldn't fail because it contains a
    .docx it doesn't know how to read yet."""
    path = Path(path)
    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED_EXTENSIONS else []
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)


def ingest_path(path: str | Path, index: Index | None = None, chunk_size: int = 500, overlap: int = 50) -> dict:
    """Full pipeline for a file or directory. Returns a summary dict rather
    than just a count -- callers (CLI, tests) need to know which files
    actually got indexed vs skipped (empty/unreadable), not just a total."""
    # NOT `index or Index()` -- Index defines __len__, so a freshly created,
    # still-empty Index (len 0) is falsy in Python, and `or` would silently
    # discard it in favor of a brand-new default-path Index. Found for real:
    # an explicitly passed, isolated, empty Index got silently swapped out
    # for the real ~/.keep/index.json mid-call, contaminating results with
    # unrelated indexed content and breaking test isolation. `is None` is
    # the only correct check here.
    index = index if index is not None else Index()
    files = discover_files(path)

    indexed_files = []
    skipped_files = []
    total_chunks = 0

    for file_path in files:
        try:
            chunks = chunk_file(file_path, chunk_size=chunk_size, overlap=overlap)
        except Exception:
            skipped_files.append(str(file_path))
            continue

        if not chunks:
            skipped_files.append(str(file_path))
            continue

        # Re-ingesting an already-indexed file replaces its chunks rather
        # than appending duplicates alongside them.
        index.remove_source(str(file_path))
        added = index.add_chunks(chunks)
        indexed_files.append(str(file_path))
        total_chunks += added

    index.save()

    return {
        "indexed_files": indexed_files,
        "skipped_files": skipped_files,
        "total_chunks": total_chunks,
        "index_size": len(index),
    }
