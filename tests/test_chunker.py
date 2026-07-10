"""Real tests for chunker.py."""

import pytest

from keep.search.chunker import chunk_file, chunk_text


def test_chunk_text_splits_with_overlap():
    text = "a" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 3
    # Overlap means the tail of one chunk and the head of the next share
    # characters -- verifying the actual overlap amount, not just "> 1 chunk".
    assert chunks[0][-50:] == chunks[1][:50]


def test_chunk_text_handles_empty_input():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_file_markdown(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("# Title\n\nSome real content here about a specific topic.")
    chunks = chunk_file(f)
    assert len(chunks) == 1
    assert "specific topic" in chunks[0].text
    assert chunks[0].source_file == str(f)


def test_chunk_file_pdf(tmp_path):
    from reportlab.pdfgen import canvas

    f = tmp_path / "statement.pdf"
    c = canvas.Canvas(str(f))
    c.drawString(72, 720, "STACKS TEST PDF EXTRACTION CHECK 8842")
    c.save()

    chunks = chunk_file(f)
    assert len(chunks) == 1
    assert "STACKS TEST PDF EXTRACTION CHECK 8842" in chunks[0].text
    assert chunks[0].page == 1


def test_chunk_file_rejects_unsupported_extension(tmp_path):
    f = tmp_path / "image.png"
    f.write_bytes(b"not a real png, just testing extension rejection")
    with pytest.raises(ValueError):
        chunk_file(f)
