"""Real (no-mock) tests for backends.py -- against actual Vision framework
calls and the actual on-device model, matching private-agent/orchard's own
"no mocks" test philosophy."""

from pathlib import Path

import pytest


def test_vision_backend_reads_real_text(text_image_path):
    from keep.vision.backends import VisionOCRBackend

    backend = VisionOCRBackend()
    text_lines, labels = backend._extract(text_image_path)
    # "contains", not exact match -- Vision's OCR can return the string with
    # different casing/spacing than what Pillow rendered, and this test
    # cares whether OCR actually recognized the content, not byte-exact
    # reproduction (same lesson as private-agent's reminder test).
    joined = " ".join(text_lines).upper()
    assert "KEEP" in joined
    assert "4471" in joined


def test_vision_backend_handles_blank_image_honestly(blank_image_path):
    from keep.vision.backends import VisionOCRBackend

    backend = VisionOCRBackend()
    text_lines, labels = backend._extract(blank_image_path)
    assert text_lines == []
    # A blank white image may still get a low-confidence classification
    # label or two from Vision -- the 0.3 confidence floor in _extract is
    # what actually matters here, not that labels is necessarily empty.


def test_describe_narrates_real_text(text_image_path):
    from keep.vision.backends import VisionOCRBackend

    backend = VisionOCRBackend()
    description = backend.describe(text_image_path)
    assert len(description) > 0
    # Loose check on content, not exact wording -- the model paraphrases;
    # what matters is it actually engaged with what Vision extracted rather
    # than returning something generic.
    assert "4471" in description or "keep" in description.lower()


def test_describe_handles_nothing_recognizable(blank_image_path):
    from keep.vision.backends import VisionOCRBackend

    backend = VisionOCRBackend()
    description = backend.describe(blank_image_path)
    assert len(description) > 0


def test_native_binary_path_resolves_to_repo_root():
    """Regression test: keep.vision is one package level deeper than
    lantern's original flat src/lantern/ layout, so _native_binary_path()'s
    dirname() chain needed one more hop than the ported original had. Verify
    it lands on the real repo-root/native/bin/... path, not one level off."""
    import keep.vision.backends as backends_module
    from keep.vision.backends import _native_binary_path

    repo_root = Path(backends_module.__file__).parents[3]
    expected = repo_root / "native" / "bin" / "lantern-native-describe"
    assert Path(_native_binary_path()) == expected


def test_active_backend_name_reflects_reality():
    from keep.vision.backends import _probe_native, active_backend_name

    # Not hardcoded to "vision" -- active_backend_name() must report
    # whichever backend _probe_native() actually finds usable right now.
    # On most machines (no beta, or a beta/OS version skew -- see
    # backends.py module docstring) that's "vision"; on a machine where the
    # native helper genuinely works it should honestly say "native".
    expected = "native" if _probe_native() else "vision"
    assert active_backend_name() == expected


def test_get_backend_returns_working_backend():
    from keep.vision.backends import get_backend

    backend = get_backend()
    assert hasattr(backend, "describe")


def test_native_backend_raises_clear_error_when_unavailable():
    from keep.vision.backends import NativeBackendUnavailableError, NativeImageBackend, _probe_native

    if _probe_native():
        pytest.skip("Native backend is actually available on this machine -- nothing to test here.")
    with pytest.raises(NativeBackendUnavailableError):
        NativeImageBackend()


def test_native_backend_describes_real_image(text_image_path):
    """Real (no-mock) end-to-end test of the native path -- only runs on a
    machine where the beta SDK/OS pairing actually works, since that's a
    real environmental precondition this repo can't fake or bypass. See
    backends.py module docstring for the Xcode-beta/OS-beta version-skew
    finding that makes this conditional necessary."""
    from keep.vision.backends import NativeImageBackend, _probe_native

    if not _probe_native():
        pytest.skip("Native backend not usable on this machine right now -- see backends.py docstring.")

    backend = NativeImageBackend()
    description = backend.describe(text_image_path)
    assert len(description) > 0
