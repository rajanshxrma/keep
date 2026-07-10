"""Core agent: a private, on-device assistant with tool-calling access to your Mac."""

from langchain_apple_foundation_models import ChatAppleFoundationModels
from langchain_core.tools import tool

from keep.router import mlx_available, needs_tools, run_afm_plain, run_mlx
from keep.tools import (
    create_calendar_event,
    create_reminder,
    describe_my_screen,
    draft_email,
    search_files,
    search_my_stuff,
)

INSTRUCTIONS = (
    "You are a private, on-device assistant running entirely on this Mac. "
    "You can search the user's files, search the CONTENTS of their indexed "
    "notes and documents, describe what's on their screen, create calendar "
    "events, create reminders, and draft (never send) emails. Be concise and "
    "direct in your answers. Always confirm what action you took."
)


def build_agent() -> ChatAppleFoundationModels:
    tools = [
        tool(search_files),
        tool(search_my_stuff),
        tool(describe_my_screen),
        tool(create_calendar_event),
        tool(create_reminder),
        tool(draft_email),
    ]
    llm = ChatAppleFoundationModels(instructions=INSTRUCTIONS)
    return llm.bind_tools(tools)


def run(prompt: str) -> str:
    # Route by whether the prompt plausibly needs a real tool -- see
    # router.py for why this isn't a model-based classifier call.
    if not needs_tools(prompt):
        # mlx-lm is an optional [mlx] extra (see router.mlx_available) --
        # without it, plain chat falls back to the on-device model directly.
        return run_mlx(prompt) if mlx_available() else run_afm_plain(prompt)
    agent = build_agent()
    result = agent.invoke(prompt)
    return result.content
