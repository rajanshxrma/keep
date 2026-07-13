"""The search_my_stuff agent tool -- retrieves the CONTENTS of the user's own
ingested notes and documents (keep.search) for the calling agent to answer
from, as opposed to files.search_files which LOCATES a file by name/path via
Spotlight.

Returns raw cited passages, no LLM call of its own (see keep.search.generator
for why: a second ChatAppleFoundationModels session created from inside a
tool call the outer agent's own generation is still in flight for hit
Apple's one-in-flight-generation-per-process constraint -- not merely slow,
a genuine deadlock, reproduced live: run() on a search question never
returned in 4+ minutes. One session flows through the whole interaction now;
the outer agent (see agent.py's INSTRUCTIONS) does the grounded synthesis
itself from what this tool returns."""

from __future__ import annotations

from keep.search.retriever import retrieve

# top_k=3, not stacks' default of 5 -- the passages have to round-trip back
# through the calling agent's own conversation, so keeping this small keeps
# the agent's context usage small too.
_TOP_K = 3


def search_my_stuff(question: str) -> str:
    """Retrieve passages from the user's ingested notes and documents
    (whatever was indexed with `keep ingest`) relevant to a question. Use
    this when the user asks what their files or notes SAY, or asks a factual
    question that might be answered by something they've saved. Use
    search_files instead when they want to LOCATE a file by name rather than
    know what's in it. The passages returned are NOT the final answer --
    read them and answer the user's actual question from them yourself,
    citing [source, page] for every claim, exactly as instructed.
    """
    results = retrieve(question, top_k=_TOP_K)
    if not results:
        return (
            "No relevant passages found in the indexed files. Tell the user "
            "you don't have information about that in their indexed files, "
            "and that running `keep ingest <path>` on a relevant file first "
            "would let you check again."
        )

    parts = [f"[{r.source_file}, page {r.page}]:\n{r.text}" for r in results]
    return "\n\n---\n\n".join(parts)
