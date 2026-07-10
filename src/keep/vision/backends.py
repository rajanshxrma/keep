"""Image-description backends for keep.

Two backends, chosen automatically at runtime, not configured by hand:

- "native": Apple's on-device Foundation Model given the image directly, via
  FoundationModels.Attachment<ImageAttachmentContent> (macOS 27 beta only --
  verified directly against the beta SDK's real .swiftinterface, not assumed
  from the WWDC26 preview description; see native/Sources/.../main.swift).
  This is a pure-Swift API surface (generics, protocols) that PyObjC cannot
  bridge at all -- verified directly too: `import FoundationModels` fails
  under PyObjC even with the beta installed. So NativeImageBackend shells
  out to a small compiled Swift helper (native/), the same pattern already
  used for /usr/sbin/screencapture in capture.py, rather than a PyObjC call.
- "vision": Apple's Vision framework (stable, mature, shipped for years) for
  OCR (VNRecognizeTextRequest) and scene/object classification
  (VNClassifyImageRequest), with the extracted text/labels handed to the
  same on-device Foundation Model for narration -- the model never sees
  pixels in this path, only Vision's structured output. This is the backend
  every clone of this repo actually gets, beta or not.

get_backend() always tries native first and falls back to vision -- never
raises for "no native backend", since not having the beta is the normal
case, not an error.

A third real finding, beyond "beta or not installed": even with the beta SDK
installed and the helper compiled successfully against it, the *compiled*
binary can still fail at *runtime* with a dyld "Symbol not found" error if
the installed OS beta build doesn't exactly match the Xcode-beta build it
was compiled against (observed directly: Xcode-beta 27A5209h's SDK declared
`Attachment.init(imageURL:orientation:)`, but the installed OS beta's actual
`/System/Library/Frameworks/FoundationModels.framework` didn't yet export
that symbol at runtime -- a real Xcode-beta/OS-beta version skew, not a bug
in this code). `_probe_native()` therefore does a real subprocess smoke-test
of the compiled binary, not just a file-existence check -- a dyld symbol
failure exits 134 immediately (before main() runs) regardless of arguments,
which is a fast, reliable, distinguishable signal from a clean "no such
image" failure (exit 2) that proves the binary actually loaded and ran.
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from typing import Protocol


class Backend(Protocol):
    def describe(self, image_path: str) -> str: ...


_NARRATION_INSTRUCTIONS = (
    "You describe images for a low-vision user, out loud. You are given only "
    "text and scene labels extracted by a computer vision system -- you have "
    "not seen the actual image. Report ONLY what's in that extracted data. "
    "Never add visual details, objects, colors, layout, or context that "
    "weren't explicitly given to you, even if they'd be a plausible guess -- "
    "a plausible-sounding invented detail is worse than no detail, because "
    "the user can't verify it themselves. If a word or label is evocative "
    "(e.g. the text 'CALENDAR' by itself), describe only that the word/label "
    "was detected -- do not imagine what a calendar in the scene might look "
    "like. One or two plain sentences, present tense, no hedging, no "
    "meta-commentary about being an AI."
)


_NATIVE_INSTRUCTIONS = (
    "You describe images for a low-vision user, out loud. You are given the "
    "actual image directly. Report only what is genuinely visible -- do not "
    "guess at things outside the frame, do not invent plausible-sounding "
    "detail you're not confident about. One or two plain sentences, present "
    "tense, no hedging, no meta-commentary about being an AI."
)


def _native_binary_path() -> str:
    # __file__ is repo_root/src/keep/vision/backends.py -- keep.vision is one
    # package level deeper than lantern's original flat src/lantern/ layout,
    # so this needs one more dirname() than lantern's own version did to
    # reach repo_root/native/bin/... (verified with a real path, not assumed).
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    return os.path.join(repo_root, "native", "bin", "lantern-native-describe")


class NativeBackendUnavailableError(RuntimeError):
    """Raised if NativeImageBackend is constructed without the native
    helper actually being usable -- callers should check _probe_native()
    (which get_backend() already does) before constructing this directly."""


class NativeImageBackend:
    """Feeds the image directly to Apple's on-device model via the compiled
    Swift helper in native/ -- see this module's docstring for why a
    subprocess rather than a PyObjC call."""

    def __init__(self):
        if not _probe_native():
            raise NativeBackendUnavailableError(
                "Native image backend isn't usable on this machine right now "
                "-- see backends.py module docstring for the real reasons "
                "this can happen (no beta SDK, or a beta OS/SDK version skew)."
            )

    def describe(self, image_path: str) -> str:
        result = subprocess.run(
            [_native_binary_path(), image_path],
            input=_NATIVE_INSTRUCTIONS,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Native backend failed: {result.stderr.strip()}")
        return result.stdout.strip()


class VisionOCRBackend:
    """Vision framework OCR + classification, narrated by the on-device model."""

    def __init__(self, instructions: str | None = None):
        from langchain_apple_foundation_models import ChatAppleFoundationModels

        self._llm = ChatAppleFoundationModels(instructions=instructions or _NARRATION_INSTRUCTIONS)

    def _extract(self, image_path: str) -> tuple[list[str], list[str]]:
        """Runs Vision's OCR + classification requests against the image.

        Returns (recognized_text_lines, top_classification_labels). Both can
        be empty -- a photo of a blank wall has no text and no confident
        classification, and that's a real, valid result, not an error.
        """
        import Quartz
        import Vision
        from Foundation import NSURL

        image_url = NSURL.fileURLWithPath_(image_path)
        handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(image_url, None)

        text_request = Vision.VNRecognizeTextRequest.alloc().init()
        text_request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)

        classify_request = Vision.VNClassifyImageRequest.alloc().init()

        success, error = handler.performRequests_error_([text_request, classify_request], None)
        if not success:
            raise RuntimeError(f"Vision request failed: {error}")

        text_lines = []
        for obs in text_request.results() or []:
            candidates = obs.topCandidates_(1)
            if candidates:
                text_lines.append(str(candidates[0].string()))

        # Classification observations are sorted by confidence; keep only
        # ones Vision itself is reasonably sure about, not the long tail.
        labels = [
            str(obs.identifier())
            for obs in (classify_request.results() or [])
            if obs.confidence() >= 0.3
        ][:5]

        return text_lines, labels

    def describe(self, image_path: str) -> str:
        text_lines, labels = self._extract(image_path)
        if not text_lines and not labels:
            return "Nothing recognizable in view -- no text and no confident scene labels."

        parts = []
        if labels:
            parts.append("Scene labels (Vision, most confident first): " + ", ".join(labels))
        if text_lines:
            parts.append("Text visible in the image: " + " / ".join(text_lines))
        context = "\n".join(parts)

        prompt = (
            f"{context}\n\nNarrate ONLY the above for someone who can't see it "
            "themselves. Do not add anything not listed above."
        )
        result = self._llm.invoke(prompt)
        return result.content


@lru_cache(maxsize=None)
def _probe_native() -> bool:
    """True only if the compiled native helper actually runs on this
    machine right now -- a real subprocess smoke-test, not just a file-
    existence check. See module docstring for why existence alone isn't
    enough (the Xcode-beta/OS-beta version-skew finding). Cached: this
    process's dyld-loadability of the binary doesn't change mid-run, so
    there's no reason to pay the subprocess cost more than once."""
    binary = _native_binary_path()
    if not os.path.exists(binary):
        return False
    try:
        # A nonexistent image path is deliberate -- cheapest possible real
        # invocation. A binary that's actually dyld-loadable reaches our
        # own "file not found" check and exits 2; a version-skewed binary
        # dies in dyld before main() ever runs, exit 134, regardless of
        # arguments -- see module docstring.
        result = subprocess.run(
            [binary, "/__keep_native_probe__"],
            input=_NATIVE_INSTRUCTIONS,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 2


@lru_cache(maxsize=None)
def _cached_vision_backend() -> VisionOCRBackend:
    return VisionOCRBackend()


def get_backend() -> Backend:
    if _probe_native():
        return NativeImageBackend()
    return _cached_vision_backend()


def active_backend_name() -> str:
    """Which backend get_backend() will actually return right now -- for
    the menu bar / CLI to show the user, and for the eval script to label
    its results honestly rather than assuming."""
    return "native" if _probe_native() else "vision"
