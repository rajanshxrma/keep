"""py2app build script for the Keep menu bar app.

Usage:
    scripts/build_app.sh

Don't run `python setup.py py2app` directly -- py2app refuses to run at all
while pyproject.toml's [project.dependencies] is present (setuptools derives
Distribution.install_requires from it, which py2app's build_app.py hard-
rejects: "install_requires is no longer supported", and no setup.py kwarg
can override a static PEP 621 field). build_app.sh moves pyproject.toml
aside for just this invocation and restores it via a trap, success or
failure -- see that script's comment for the full explanation.

Deliberately unsigned -- no Apple Developer Program account (see README's
first-run notes). The version comes from src/keep/__init__.py, not a
literal here, so pyproject.toml, keep.__version__, and this bundle's
CFBundleShortVersionString can never drift out of sync the way an earlier
project in this portfolio's history once did (see scripts/check_version.py).
"""

import re
from pathlib import Path

from setuptools import setup


def _read_version() -> str:
    text = Path("src/keep/__init__.py").read_text()
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise RuntimeError("Could not find __version__ in src/keep/__init__.py")
    return match.group(1)


VERSION = _read_version()

APP = ["src/keep/menubar.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Keep",
        "CFBundleDisplayName": "Keep",
        "CFBundleIdentifier": "com.rajansharma.keep",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSUIElement": True,
    },
    "packages": [
        "keep",
        "rumps",
        "langchain_apple_foundation_models",
    ],
}

setup(
    app=APP,
    name="Keep",
    version=VERSION,
    options={"py2app": OPTIONS},
    data_files=DATA_FILES,
    setup_requires=["py2app"],
    install_requires=[],
)
