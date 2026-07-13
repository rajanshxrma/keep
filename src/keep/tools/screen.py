"""The describe_my_screen agent tool -- describes what's currently visible
on the user's screen, entirely on-device (Vision OCR/classification narrated
by the on-device model; see keep.vision.backends). Zero-arg by design: the
simplest possible tool schema for a 3B-class on-device model to call
correctly."""

from __future__ import annotations

import os

from keep.vision.backends import get_backend
from keep.vision.capture import CaptureError, capture_screen


def describe_my_screen() -> str:
    """Describe what is currently visible on the user's screen. Use this
    when the user asks what's on their screen, what they're looking at, or
    to describe/read the current window out loud."""
    # The menu-item path (menubar.py's "Describe my screen" click handler)
    # wraps this whole call in a broad except-Exception and shows
    # CaptureError's own message directly -- genuinely helpful (e.g. the
    # Screen Recording permission hint on first run). This is the *other*
    # path to the same tool -- the agent calling it itself, e.g. a typed
    # "what's on my screen" -- which had no equivalent catch: an uncaught
    # CaptureError propagated out through the tool-calling layer and
    # surfaced as a raw internals blob instead (verified in the pre-launch
    # audit). Catching here, with the same message shape, covers both paths.
    try:
        path = capture_screen()
    except CaptureError as exc:
        return f"Couldn't capture the screen: {exc}"
    try:
        return get_backend().describe(path)
    finally:
        os.remove(path)
