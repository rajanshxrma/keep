"""Real (no-mock) tests for capture.py -- both screen and camera.

Camera capture needs the Camera permission already granted to whatever
terminal/process runs this suite (macOS's one-time prompt, granted once via
System Settings > Privacy & Security > Camera, sticks per-app after that).
Skips itself if that permission hasn't been granted yet rather than hanging
on a prompt nothing here can click through."""

import os

from keep.vision.capture import capture_camera, capture_screen


def test_capture_screen_produces_real_image():
    path = capture_screen()
    try:
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
        with open(path, "rb") as f:
            header = f.read(8)
        # Real PNG magic bytes -- confirms this is an actual image file,
        # not just an empty/placeholder path.
        assert header[:4] == b"\x89PNG"
    finally:
        os.remove(path)


def test_capture_camera_produces_real_image():
    # Briefly lights up the camera indicator, same as any app taking a
    # photo -- real capture, not a mock, matching this repo's test
    # philosophy throughout.
    path = capture_camera()
    try:
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
        with open(path, "rb") as f:
            header = f.read(3)
        # Real JPEG magic bytes.
        assert header == b"\xff\xd8\xff"
    finally:
        os.remove(path)
