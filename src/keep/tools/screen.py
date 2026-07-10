"""The describe_my_screen agent tool -- describes what's currently visible
on the user's screen, entirely on-device (Vision OCR/classification narrated
by the on-device model; see keep.vision.backends). Zero-arg by design: the
simplest possible tool schema for a 3B-class on-device model to call
correctly."""

from __future__ import annotations

import os

from keep.vision.backends import get_backend
from keep.vision.capture import capture_screen


def describe_my_screen() -> str:
    """Describe what is currently visible on the user's screen. Use this
    when the user asks what's on their screen, what they're looking at, or
    to describe/read the current window out loud."""
    path = capture_screen()
    try:
        return get_backend().describe(path)
    finally:
        os.remove(path)
