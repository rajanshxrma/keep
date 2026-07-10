"""Real tests for ingest.py -- real files, real discovery, real indexing."""

from keep.search.index import Index
from keep.search.ingest import discover_files, ingest_path


def test_discover_files_finds_supported_only(tmp_path):
    (tmp_path / "note.md").write_text("real content")
    (tmp_path / "note.txt").write_text("real content")
    (tmp_path / "image.png").write_bytes(b"not indexable")

    found = discover_files(tmp_path)
    names = {p.name for p in found}
    assert names == {"note.md", "note.txt"}


def test_ingest_path_indexes_a_directory(sample_docs_dir, isolated_index_path):
    idx = Index(path=isolated_index_path)
    result = ingest_path(sample_docs_dir, index=idx)

    assert len(result["indexed_files"]) == 2
    assert result["total_chunks"] > 0
    assert result["skipped_files"] == []


def test_reingesting_a_file_replaces_rather_than_duplicates(tmp_path, isolated_index_path):
    f = tmp_path / "note.md"
    f.write_text("original content about topic A")
    idx = Index(path=isolated_index_path)

    ingest_path(f, index=idx)
    first_size = len(idx)

    ingest_path(f, index=idx)
    second_size = len(idx)

    assert first_size == second_size


def test_ingest_skips_empty_file(tmp_path, isolated_index_path):
    (tmp_path / "empty.txt").write_text("")
    idx = Index(path=isolated_index_path)
    result = ingest_path(tmp_path, index=idx)

    assert result["indexed_files"] == []
    assert len(result["skipped_files"]) == 1
