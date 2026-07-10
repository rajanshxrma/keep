"""Image capture sources for keep -- screen and camera.

Screen capture shells out to /usr/sbin/screencapture rather than driving
ScreenCaptureKit directly. Both are stable, non-beta APIs, but screencapture
is a single well-tested system binary Apple has shipped and maintained for
two decades, with permission handling (Screen Recording, prompted once by
the OS) already solved -- the same "shell out to a stable OS tool instead of
re-implementing its permission/plumbing story" choice private-agent already
makes for AppleScript (see tools/_applescript.py there). Reaching for
ScreenCaptureKit's own async, delegate-based capture API would mean
re-solving problems screencapture has already solved, for no behavioral
difference keep needs.

Camera capture does use AVFoundation directly (via PyObjC) -- there's no
simple CLI equivalent, and a single still frame from the default camera is
a small, well-bounded piece of that API surface.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path


class CaptureError(RuntimeError):
    """Raised when a capture genuinely fails (not just 'nothing recognizable
    in the result' -- that's a valid describe() outcome, not a capture
    error)."""


def capture_screen() -> str:
    """Captures the whole main screen to a temp PNG, returns its path.

    Raises CaptureError if /usr/sbin/screencapture exits non-zero (e.g.
    Screen Recording permission not yet granted -- macOS handles that
    permission prompt itself on first use; this just surfaces failure
    clearly rather than returning a path to a file that doesn't exist).
    """
    out_path = Path(tempfile.gettempdir()) / f"keep-screen-{int(time.time() * 1000)}.png"
    result = subprocess.run(
        ["/usr/sbin/screencapture", "-x", str(out_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0 or not out_path.exists():
        raise CaptureError(
            f"screencapture failed (exit {result.returncode}): {result.stderr.strip()}. "
            "If this is the first run, check System Settings > Privacy & Security > "
            "Screen Recording for this terminal/app."
        )
    return str(out_path)


def capture_camera(device_index: int = 0) -> str:
    """Captures a single still frame from the default camera, returns its path.

    Raises CaptureError on any AVFoundation-side failure, including camera
    permission not yet granted (macOS prompts for Camera access on first
    use, same one-time-grant pattern as Screen Recording above).
    """
    import AVFoundation
    import Quartz
    from Foundation import NSURL

    devices = AVFoundation.AVCaptureDevice.devicesWithMediaType_(AVFoundation.AVMediaTypeVideo)
    if not devices or device_index >= len(devices):
        raise CaptureError("No camera device found.")
    device = devices[device_index]

    session = AVFoundation.AVCaptureSession.alloc().init()
    input_, error = AVFoundation.AVCaptureDeviceInput.deviceInputWithDevice_error_(device, None)
    if input_ is None:
        raise CaptureError(f"Could not open camera input: {error}")
    session.addInput_(input_)

    output = AVFoundation.AVCaptureStillImageOutput.alloc().init()
    session.addOutput_(output)
    session.startRunning()

    # AVCaptureStillImageOutput's capture callback is async; give the
    # session a moment to actually produce a frame before tearing it down.
    # A short fixed sleep rather than a callback/semaphore dance -- this is
    # a one-shot CLI-style capture, not a live video pipeline, so simplicity
    # wins over doing this the "proper" async way.
    connection = output.connectionWithMediaType_(AVFoundation.AVMediaTypeVideo)
    if connection is None:
        session.stopRunning()
        raise CaptureError("No video connection available on the capture session.")

    captured = {}

    def _on_complete(buffer, error):
        captured["buffer"] = buffer
        captured["error"] = error

    output.captureStillImageAsynchronouslyFromConnection_completionHandler_(connection, _on_complete)

    waited = 0.0
    while "buffer" not in captured and waited < 5.0:
        time.sleep(0.05)
        waited += 0.05
    session.stopRunning()

    if captured.get("error") is not None:
        raise CaptureError(f"Camera capture failed: {captured['error']}")
    if "buffer" not in captured or captured["buffer"] is None:
        raise CaptureError("Camera capture timed out with no frame.")

    image_data = AVFoundation.AVCaptureStillImageOutput.jpegStillImageNSDataRepresentation_(
        captured["buffer"]
    )
    out_path = Path(tempfile.gettempdir()) / f"keep-camera-{int(time.time() * 1000)}.jpg"
    image_data.writeToFile_atomically_(str(out_path), True)
    if not out_path.exists():
        raise CaptureError("Camera frame captured but failed to write to disk.")
    return str(out_path)
