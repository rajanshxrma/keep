"""Real tests for the search_my_stuff agent tool -- real embeddings, real
on-device generation. The only thing stubbed is *which* Index retrieve()
reads from, so the test never touches the user's real ~/.keep/index.json;
the retrieval and generation logic underneath is exercised for real."""

import keep.tools.stuff as stuff_module
from keep.search.ingest import ingest_path
from keep.search.index import Index


def test_search_my_stuff_returns_grounded_answer_with_sources(sample_docs_dir, isolated_index_path, monkeypatch):
    idx = Index(path=isolated_index_path)
    ingest_path(sample_docs_dir, index=idx)
    monkeypatch.setattr(
        stuff_module, "retrieve", lambda question, top_k=3: idx.search(question, top_k=top_k, min_similarity=0.2)
    )

    result = stuff_module.search_my_stuff("how many vacation days do employees get")

    assert "15" in result
    assert "Sources:" in result
    assert "handbook" in result.lower()


def test_search_my_stuff_omits_sources_on_honest_fallback(sample_docs_dir, isolated_index_path, monkeypatch):
    idx = Index(path=isolated_index_path)
    ingest_path(sample_docs_dir, index=idx)
    monkeypatch.setattr(
        stuff_module, "retrieve", lambda question, top_k=3: idx.search(question, top_k=top_k, min_similarity=0.5)
    )

    # Nothing in the sample docs is remotely related -- no chunk clears even
    # a permissive similarity floor, so the honest fallback fires with no
    # citations, and the "Sources:" suffix must not be appended to it.
    result = stuff_module.search_my_stuff("what is the capital of France")

    assert "don't have information" in result.lower()
    assert "Sources:" not in result
