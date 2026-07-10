"""Query the local index -- the on-device replacement for finance-rag's
retriever.py (which called Supabase's match_documents RPC)."""

from __future__ import annotations

from keep.search.index import Index, SearchResult


def retrieve(query: str, index: Index | None = None, top_k: int = 5, min_similarity: float = 0.2) -> list[SearchResult]:
    # See ingest.py's identical comment: `index or Index()` is wrong here --
    # an empty (len 0) Index is falsy, so `or` would silently swap it for
    # the default-path Index instead of using the one actually passed in.
    index = index if index is not None else Index()
    return index.search(query, top_k=top_k, min_similarity=min_similarity)
