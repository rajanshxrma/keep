"""The search_my_stuff agent tool -- answers questions from the CONTENTS of
the user's own ingested notes and documents (keep.search), as opposed to
files.search_files which LOCATES a file by name/path via Spotlight.

Runs its own retrieve -> generate_answer round trip and returns only the
finished short answer string. The retrieved context (up to a few thousand
characters across top_k chunks) never enters the calling agent's own
conversation -- it lives entirely inside this tool's internal on-device
session, so it never threatens the agent's 4096-token window."""

from __future__ import annotations

from keep.search.generator import generate_answer
from keep.search.retriever import retrieve

# top_k=3, not stacks' default of 5 -- the answer has to round-trip back
# through the calling agent's own conversation, so keeping the internal
# context small keeps the returned answer short too.
_TOP_K = 3


def search_my_stuff(question: str) -> str:
    """Answer a question using the CONTENTS of the user's ingested notes and
    documents (whatever was indexed with `keep ingest`). Use this when the
    user asks what their files or notes SAY, or asks a factual question that
    might be answered by something they've saved. Use search_files instead
    when they want to LOCATE a file by name rather than know what's in it.
    """
    results = retrieve(question, top_k=_TOP_K)
    answer = generate_answer(question, results)

    if not answer.citations:
        return answer.text

    sources = ", ".join(f"{c.source_file} p.{c.page}" for c in answer.citations)
    return f"{answer.text}\n\nSources: {sources}"
