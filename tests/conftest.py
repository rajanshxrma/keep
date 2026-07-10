"""Shared fixtures for real (no-mock) tests, matching the rest of this
portfolio's testing philosophy."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _skip_if_apple_intelligence_unavailable():
    from langchain_apple_foundation_models import ChatAppleFoundationModels

    try:
        ChatAppleFoundationModels()
    except Exception as e:
        pytest.skip(f"Apple Foundation Models not available: {e}")


@pytest.fixture
def sample_docs_dir(tmp_path: Path) -> Path:
    """A small, real, deterministic set of documents to ingest -- distinct
    enough topics that retrieval has something real to discriminate
    between, not near-duplicate filler."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    (docs_dir / "handbook.md").write_text(
        "# Company Handbook\n\n"
        "## Vacation Policy\n"
        "Employees accrue 15 days of paid vacation per year, credited monthly "
        "at 1.25 days per month. Unused vacation carries over up to a maximum "
        "of 10 days into the next calendar year.\n\n"
        "## Remote Work\n"
        "Employees may work remotely up to 3 days per week with manager approval."
    )
    (docs_dir / "recipe.txt").write_text(
        "Simple tomato soup: saute one diced onion in olive oil until translucent, "
        "add two cans of crushed tomatoes and a cup of vegetable stock, simmer for "
        "20 minutes, then blend until smooth and stir in a splash of cream."
    )
    return docs_dir


@pytest.fixture
def isolated_index_path(tmp_path: Path) -> Path:
    """A real Index instance's storage path, isolated to this test's own
    tmp_path -- never the real ~/.keep/index.json, so tests can never
    read or clobber the user's actual indexed file content."""
    return tmp_path / "test_index.json"
