"""Real tests for index.py -- real embeddings, real cosine search, real
on-disk persistence with an isolated path (never the real ~/.keep/index.json)."""

import os

from keep.search.chunker import Chunk
from keep.search.index import Index


def test_add_and_search_finds_relevant_chunk(isolated_index_path):
    idx = Index(path=isolated_index_path)
    idx.add_chunks(
        [
            Chunk(text="Employees accrue 15 days of paid vacation per year.", page=1, index=0, source_file="a.md"),
            Chunk(text="Simple tomato soup: saute onion, add crushed tomatoes.", page=1, index=1, source_file="b.txt"),
        ]
    )

    results = idx.search("how much vacation time do I get", top_k=5, min_similarity=0.0)
    assert len(results) == 2
    # The vacation chunk should rank above the soup recipe for a vacation query.
    assert "vacation" in results[0].text.lower()
    assert results[0].similarity > results[1].similarity


def test_min_similarity_filters_irrelevant_results(isolated_index_path):
    idx = Index(path=isolated_index_path)
    idx.add_chunks([Chunk(text="Simple tomato soup recipe with onion and cream.", page=1, index=0, source_file="b.txt")])

    results = idx.search("quarterly financial earnings report", top_k=5, min_similarity=0.5)
    assert results == []


def test_remove_source_drops_only_that_files_chunks(isolated_index_path):
    idx = Index(path=isolated_index_path)
    idx.add_chunks(
        [
            Chunk(text="content from file a", page=1, index=0, source_file="a.md"),
            Chunk(text="content from file b", page=1, index=0, source_file="b.md"),
        ]
    )
    removed = idx.remove_source("a.md")
    assert removed == 1
    assert idx.indexed_sources() == {"b.md"}


def test_save_and_load_roundtrips(isolated_index_path):
    idx = Index(path=isolated_index_path)
    idx.add_chunks([Chunk(text="persisted content", page=1, index=0, source_file="a.md")])
    idx.save()

    reloaded = Index(path=isolated_index_path)
    assert len(reloaded) == 1
    results = reloaded.search("persisted content", min_similarity=0.0)
    assert len(results) == 1


def test_saved_index_has_restricted_permissions(isolated_index_path):
    idx = Index(path=isolated_index_path)
    idx.add_chunks([Chunk(text="sensitive personal content", page=1, index=0, source_file="a.md")])
    idx.save()

    mode = oct(os.stat(isolated_index_path).st_mode)[-3:]
    assert mode == "600"


def test_reads_legacy_stacks_index_when_new_path_absent(tmp_path, monkeypatch):
    """Regression test for the stacks->keep migration: a previously-ingested
    ~/.stacks/index.json must stay searchable in Keep without re-ingesting."""
    import keep.search.index as index_module

    legacy_path = tmp_path / "legacy" / "index.json"
    new_path = tmp_path / "new" / "index.json"
    monkeypatch.setattr(index_module, "LEGACY_INDEX_PATH", legacy_path)
    monkeypatch.setattr(index_module, "DEFAULT_INDEX_PATH", new_path)

    # Seed a legacy index directly, as stacks would have left behind.
    seed = index_module.Index(path=legacy_path)
    seed.add_chunks([Chunk(text="legacy content from stacks", page=1, index=0, source_file="old.md")])
    seed.save()
    assert not new_path.exists()

    # Constructing at the new default path transparently reads the legacy file.
    idx = index_module.Index(path=new_path)
    assert len(idx) == 1
    results = idx.search("legacy content", min_similarity=0.0)
    assert len(results) == 1

    # Saving completes the migration: the new path gets its own copy.
    idx.save()
    assert new_path.exists()
