"""Real end-to-end tests: ingest -> retrieve -> generate, against the real
on-device model. No mocks -- matching this portfolio's testing philosophy
throughout."""

from keep.search.generator import generate_answer
from keep.search.index import Index
from keep.search.ingest import ingest_path
from keep.search.retriever import retrieve


def test_grounded_answer_cites_the_real_source(sample_docs_dir, isolated_index_path):
    idx = Index(path=isolated_index_path)
    ingest_path(sample_docs_dir, index=idx)

    results = retrieve("how many vacation days do employees get", index=idx, top_k=3)
    answer = generate_answer("how many vacation days do employees get", results)

    assert "15" in answer.text
    assert len(answer.citations) > 0
    assert any("handbook" in c.source_file for c in answer.citations)


def test_honest_fallback_for_unindexed_topic(sample_docs_dir, isolated_index_path):
    idx = Index(path=isolated_index_path)
    ingest_path(sample_docs_dir, index=idx)

    # Nothing in the sample docs (vacation policy, tomato soup) is remotely
    # related to this -- the honest "I don't have information" path must
    # fire rather than the model inventing a plausible-sounding answer.
    results = retrieve("what is the capital of France", index=idx, top_k=3)
    answer = generate_answer("what is the capital of France", results)

    assert "don't have information" in answer.text.lower()
    assert answer.citations == []
