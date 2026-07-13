"""Real tests for the search_my_stuff agent tool -- real embeddings, no LLM
call of its own (see stuff.py's module docstring: a nested
ChatAppleFoundationModels session here, invoked from a tool the outer agent
calls mid-generation, deadlocked against Apple's one-in-flight-generation
constraint -- reproduced live, run() on a search question never returned in
4+ minutes). This tool returns raw cited passages now; the outer agent does
the grounded synthesis (see test_agent.py for that half, exercised through
the real agent). The only thing stubbed here is *which* Index retrieve()
reads from, so the test never touches the user's real ~/.keep/index.json."""

import keep.tools.stuff as stuff_module
from keep.search.ingest import ingest_path
from keep.search.index import Index


def test_search_my_stuff_returns_labeled_passages(sample_docs_dir, isolated_index_path, monkeypatch):
    idx = Index(path=isolated_index_path)
    ingest_path(sample_docs_dir, index=idx)
    monkeypatch.setattr(
        stuff_module, "retrieve", lambda question, top_k=3: idx.search(question, top_k=top_k, min_similarity=0.2)
    )

    result = stuff_module.search_my_stuff("how many vacation days do employees get")

    # The real retrieved chunk text, not a synthesized answer -- "15" comes
    # from the source doc itself, not from any LLM call this tool makes.
    assert "15" in result
    assert "handbook" in result.lower()
    assert "[" in result and ", page" in result  # the [source, page]: label


def test_search_my_stuff_honest_fallback_for_unindexed_topic(sample_docs_dir, isolated_index_path, monkeypatch):
    idx = Index(path=isolated_index_path)
    ingest_path(sample_docs_dir, index=idx)
    monkeypatch.setattr(
        stuff_module, "retrieve", lambda question, top_k=3: idx.search(question, top_k=top_k, min_similarity=0.5)
    )

    # Nothing in the sample docs is remotely related -- no chunk clears even
    # a permissive similarity floor, so the honest no-results path fires.
    result = stuff_module.search_my_stuff("what is the capital of France")

    assert "don't have information" in result.lower()
    assert "[" not in result  # no passage labels -- nothing was retrieved


def test_search_my_stuff_never_touches_the_model(sample_docs_dir, isolated_index_path, monkeypatch):
    """Regression guard for the deadlock fix: this tool must never construct
    a ChatAppleFoundationModels session of its own. If it ever does again
    (someone re-adds an LLM call to "improve" the raw passages), this fails
    loudly instead of the bug only surfacing as an intermittent hang when
    called from inside a real agent's tool loop."""
    import langchain_apple_foundation_models

    idx = Index(path=isolated_index_path)
    ingest_path(sample_docs_dir, index=idx)
    monkeypatch.setattr(
        stuff_module, "retrieve", lambda question, top_k=3: idx.search(question, top_k=top_k, min_similarity=0.2)
    )

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("search_my_stuff must not construct its own model session")

    monkeypatch.setattr(
        langchain_apple_foundation_models, "ChatAppleFoundationModels", _fail_if_called
    )

    result = stuff_module.search_my_stuff("how many vacation days do employees get")
    assert "15" in result
