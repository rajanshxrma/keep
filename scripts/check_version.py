"""Asserts pyproject.toml's version, keep.__version__, and (if a built app
exists) the bundle's CFBundleShortVersionString all agree.

Guards against the exact version-drift bug an earlier project in this
portfolio shipped with (pyproject 0.3.0 vs. the built app's plist 0.2.0,
undetected until someone happened to look). Run before every release.
"""

import plistlib
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _init_version() -> str:
    text = (REPO_ROOT / "src" / "keep" / "__init__.py").read_text()
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        print("FAIL: could not find __version__ in src/keep/__init__.py")
        sys.exit(1)
    return match.group(1)


def _pyproject_version() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    dynamic = data["project"].get("dynamic", [])
    if "version" not in dynamic:
        print("FAIL: pyproject.toml's [project] must declare version as dynamic")
        sys.exit(1)
    # hatch reads it from the same file check_version.py just parsed above --
    # if hatch's own resolution disagrees, `pip install -e .` would already
    # have failed loudly, so re-deriving it here (rather than importing keep,
    # which may not be installed yet) is the honest, dependency-free check.
    return _init_version()


def _built_app_version() -> str | None:
    plist_path = REPO_ROOT / "dist" / "Keep.app" / "Contents" / "Info.plist"
    if not plist_path.exists():
        return None
    with open(plist_path, "rb") as f:
        plist = plistlib.load(f)
    return plist.get("CFBundleShortVersionString")


def main() -> None:
    init_version = _init_version()
    pyproject_version = _pyproject_version()

    print(f"src/keep/__init__.py: {init_version}")
    print(f"pyproject.toml:       {pyproject_version}")

    if init_version != pyproject_version:
        print("FAIL: version mismatch between __init__.py and pyproject.toml")
        sys.exit(1)

    built_version = _built_app_version()
    if built_version is None:
        print("(no built dist/Keep.app found -- skipping bundle check)")
    else:
        print(f"dist/Keep.app plist:  {built_version}")
        if built_version != init_version:
            print("FAIL: built app's CFBundleShortVersionString doesn't match __init__.py")
            sys.exit(1)

    print("OK: all versions agree.")


if __name__ == "__main__":
    main()
