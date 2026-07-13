"""Local, on-disk semantic index -- the on-device replacement for
finance-rag's Supabase pgvector table.

Brute-force cosine similarity over numpy arrays, not a real vector database
(faiss/chroma/hnswlib) -- deliberate, not a corner cut: this indexes a
person's own files (thousands, not millions, of chunks), and numpy handles
that scale in well under a second (measured, see eval script). Reaching for
a real ANN index would add a real dependency and real complexity for a
speed problem that doesn't exist at this scale.

Stored at ~/.keep/index.json by default, outside the repo (also
git-ignored as a second safeguard, see .gitignore) and created with 0600
permissions -- this file contains real snippets of the user's own
documents, so it gets the same "not world-readable" treatment as an SSH key,
not left at default umask permissions.

If a stacks-era ~/.stacks/index.json exists and the new path doesn't yet,
Index reads the legacy file on init so previously-ingested content stays
searchable without re-ingesting -- the next save() writes to the new
~/.keep/index.json path, completing the migration.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from keep.search.chunker import Chunk
from keep.search.embeddings import cosine_similarity, embed

DEFAULT_INDEX_PATH = Path.home() / ".keep" / "index.json"
LEGACY_INDEX_PATH = Path.home() / ".stacks" / "index.json"


@dataclass
class IndexedChunk:
    text: str
    page: int
    index: int
    source_file: str
    embedding: list[float]


@dataclass
class SearchResult:
    text: str
    similarity: float
    page: int
    chunk_index: int
    source_file: str


class Index:
    def __init__(self, path: Path = DEFAULT_INDEX_PATH):
        self.path = Path(path)
        self._chunks: list[IndexedChunk] = []
        if self.path.exists():
            self.load()
        elif self.path == DEFAULT_INDEX_PATH and LEGACY_INDEX_PATH.exists():
            # One-time migration: read stacks' old index so its content is
            # searchable immediately; the next save() writes it out at the
            # new path, after which this branch never fires again.
            self.load(LEGACY_INDEX_PATH)

    def add_chunks(self, chunks: list[Chunk]) -> int:
        added = 0
        for chunk in chunks:
            vector = embed(chunk.text)
            self._chunks.append(
                IndexedChunk(
                    text=chunk.text,
                    page=chunk.page,
                    index=chunk.index,
                    source_file=chunk.source_file,
                    embedding=vector.tolist(),
                )
            )
            added += 1
        return added

    def remove_source(self, source_file: str) -> int:
        """Drops every chunk for a given source file -- used before
        re-ingesting a file that's already indexed, so re-running ingest on
        an edited file doesn't just accumulate stale duplicate chunks
        alongside the fresh ones."""
        before = len(self._chunks)
        self._chunks = [c for c in self._chunks if c.source_file != source_file]
        return before - len(self._chunks)

    def indexed_sources(self) -> set[str]:
        return {c.source_file for c in self._chunks}

    def __len__(self) -> int:
        return len(self._chunks)

    def search(self, query: str, top_k: int = 5, min_similarity: float = 0.2) -> list[SearchResult]:
        # 0.2, not a stricter cutoff like 0.3: measured directly, in stacks'
        # own eval script before this code merged into Keep, that NLEmbedding's
        # cosine scores for a genuinely relevant chunk can land just under 0.3
        # while an unrelated chunk sharing surface structure (e.g. both are
        # markdown docs with a "# Title" header) scores higher. Rather than chase a
        # perfect numeric cutoff, this stays permissive here and leans on
        # generator.py's own "only answer from context, say so if it
        # doesn't apply" instructions to do the real filtering -- verified
        # this doesn't reintroduce false positives: an unrelated query still
        # correctly returns zero results and the honest fallback.
        if not self._chunks:
            return []

        query_vec = embed(query)
        scored = []
        for c in self._chunks:
            sim = cosine_similarity(query_vec, np.array(c.embedding, dtype=np.float32))
            if sim >= min_similarity:
                scored.append((sim, c))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            SearchResult(
                text=c.text, similarity=round(sim, 4), page=c.page, chunk_index=c.index, source_file=c.source_file
            )
            for sim, c in scored[:top_k]
        ]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file in the same directory, then os.replace() into
        # place -- a crash/kill/power-loss mid-write to the real path would
        # otherwise leave truncated JSON that load() can't parse (see
        # load()'s own comment for what that does to every future ingest
        # and search). os.replace() is atomic on the same filesystem, so
        # index.json is always either the old complete content or the new
        # complete content, never a partial write. The 0600 permission is
        # set on the temp file before it's ever visible at the real path
        # (via the os.open mode, not a chmod after the fact) -- real
        # personal document content lives in this file, so it never sits
        # briefly at the default umask like the old open()-then-chmod order
        # allowed.
        tmp_path = self.path.with_suffix(".json.tmp")
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump([asdict(c) for c in self._chunks], f)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise
        os.replace(tmp_path, self.path)

    def load(self, path: Path | None = None) -> None:
        load_path = path or self.path
        with open(load_path) as f:
            try:
                raw = json.load(f)
            except json.JSONDecodeError:
                # A truncated/corrupt index used to brick every future
                # ingest and search forever (json.load raising here
                # propagated straight out of Index(), which every caller
                # constructs fresh) until the user somehow knew to go
                # hand-delete a hidden file (verified in the pre-launch
                # audit). Preserve the bad file for inspection instead of
                # silently discarding it, and start clean rather than
                # crash -- an empty index that works is better than a
                # permanently broken one.
                corrupt_path = load_path.with_name(load_path.name + ".corrupt")
                load_path.rename(corrupt_path)
                print(
                    f"Keep's search index at {load_path} was corrupted and has "
                    f"been moved to {corrupt_path}. Starting with an empty "
                    "index -- run `keep ingest` again to rebuild it."
                )
                self._chunks = []
                return
        self._chunks = [IndexedChunk(**row) for row in raw]
