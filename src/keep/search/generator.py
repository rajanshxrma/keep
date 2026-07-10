"""Grounded answer generation -- the on-device replacement for finance-rag's
generator.py (which called OpenAI's chat completions). Same discipline:
answer only from retrieved context, cite sources, admit when nothing
relevant was found rather than guessing."""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_apple_foundation_models import ChatAppleFoundationModels

from keep.search.index import SearchResult


@dataclass
class Citation:
    source_file: str
    page: int
    chunk_index: int
    text_snippet: str


@dataclass
class Answer:
    text: str
    citations: list = field(default_factory=list)
    confidence: float = 0.0
    source_count: int = 0


_INSTRUCTIONS = (
    "You are a personal assistant answering questions about the user's own local "
    "files, entirely on-device. Rules: ONLY answer based on the provided context "
    "passages. Cite every claim with [source, page]. If the context doesn't "
    "contain relevant information, say plainly that you don't have information "
    "about that in the indexed files -- never guess or make something up. Be "
    "concise and specific."
)


def generate_answer(query: str, retrieved: list[SearchResult]) -> Answer:
    if not retrieved:
        return Answer(
            text="I don't have information about that in your indexed files. "
            "Try running `keep ingest <path>` on a relevant file first.",
        )

    context_parts = []
    citations = []
    for r in retrieved:
        label = f"[{r.source_file}, page {r.page}]"
        context_parts.append(f"{label}:\n{r.text}")
        citations.append(
            Citation(source_file=r.source_file, page=r.page, chunk_index=r.chunk_index, text_snippet=r.text[:150])
        )
    context = "\n\n---\n\n".join(context_parts)

    llm = ChatAppleFoundationModels(instructions=_INSTRUCTIONS)
    prompt = f"Context:\n{context}\n\nQuestion: {query}"
    result = llm.invoke(prompt)

    avg_similarity = sum(r.similarity for r in retrieved) / len(retrieved)

    return Answer(
        text=result.content,
        citations=citations,
        confidence=round(avg_similarity, 3),
        source_count=len(retrieved),
    )
