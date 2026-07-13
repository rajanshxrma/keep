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
import sysconfig
from pathlib import Path

from setuptools import setup


def _read_version() -> str:
    text = Path("src/keep/__init__.py").read_text()
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise RuntimeError("Could not find __version__ in src/keep/__init__.py")
    return match.group(1)


def _loose_top_level_so_files() -> list[str]:
    """Every compiled .so sitting directly in site-packages, not inside any
    package directory -- e.g. charset_normalizer's "ada92cb5d92a588d1b93__
    mypyc.cpython-*.so" (a shared runtime its mypyc-compiled cd/md
    submodules import by that generated name, hash changes on a
    charset_normalizer version bump) and cryptography's "_cffi_backend"
    (imported the same loose way by cryptography.hazmat's Rust/cffi
    bindings). py2app's automatic dependency scan doesn't discover either
    -- they're not inside the package that imports them, so nothing in the
    import graph analysis points at them -- and the built app crashes the
    moment the importing code path actually runs
    ("ModuleNotFoundError: No module named '<name>'"), both reproduced
    directly on real rebuilds, not assumed to generalize from one case.

    Returns real file paths for direct data_files copying, not module names
    for "includes": a loose .so named this way still gets folded into the
    zipped-modules bundle under "includes" on this py2app/Python
    combination (also reproduced directly -- an early version of this fix
    used "includes" and it stopped working once enough *other* packages
    were added elsewhere in OPTIONS, which apparently shifts py2app's own
    zip-vs-extract heuristics), and a compiled extension can never be
    imported from inside a zip at all, ever. A direct data_files copy into
    the real lib directory sidesteps that heuristic entirely -- it's just a
    file copy, not a packaging decision. Discovered by scanning for loose
    .so files here, not a hardcoded list of names, so this covers whichever
    one of these turns up next too, not just the two found so far.
    """
    site_packages = Path(sysconfig.get_path("purelib"))
    return [str(p) for p in site_packages.glob("*.so")]


def _packages_with_native_extensions() -> list[str]:
    """Every top-level site-packages directory containing a compiled .so
    anywhere inside it. Python cannot import a compiled extension from
    inside a zip archive at all (zipimport has no C-extension support) --
    py2app's default treatment for anything not explicitly listed in
    "packages" is to fold pure-Python modules into a zip for size, and it
    does this per-module without checking whether a sibling file in the
    same package happens to be a compiled .so. Forcing every such
    package to be listed in "packages" (which extracts the whole directory
    as real files instead) is what applefoundationmodels needed for its
    own dylib, and pydantic_core needed for the exact same reason,
    discovered only by a real rebuild-and-launch cycle (the build succeeds
    and even *launches* clean either way -- this class of bug only
    surfaces the moment the affected import path actually runs, which is
    exactly why build_app.sh verifies a real question gets answered, not
    just that the bundle launches). Scanning site-packages here, rather
    than hand-listing packages one crash at a time, covers every current
    and future compiled dependency in one pass instead of the same
    discovery cycle repeating for whichever one gets hit next.
    """
    site_packages = Path(sysconfig.get_path("purelib"))
    _skip = {
        # Test-only; not structured as a normal top-level import, so
        # py2app's "packages" resolution fails outright trying to locate it
        # (confirmed by a real build failure).
        "PyObjCTest",
    }
    found = set()
    for so in site_packages.rglob("*.so"):
        top = so.relative_to(site_packages).parts[0]
        if top.endswith(".so") or top in _skip:
            continue  # a loose top-level .so, not a package -- _loose_top_level_so_files handles these
        found.add(top)
    return sorted(found)


VERSION = _read_version()

APP = ["src/keep/menubar.py"]
DATA_FILES = [
    # See _loose_top_level_so_files()'s docstring for why this is a direct
    # file copy (data_files) rather than "includes" -- destination matches
    # where "packages" entries land (Contents/Resources/lib/python3.14),
    # the real sys.path directory at runtime, so a plain top-level import
    # of the module name finds it.
    ("lib/python3.14", _loose_top_level_so_files()),
]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/Keep.icns",
    "plist": {
        "CFBundleName": "Keep",
        "CFBundleDisplayName": "Keep",
        "CFBundleIdentifier": "com.rajansharma.keep",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSUIElement": True,
        # Without these, TCC silently denies the first calendar/reminders/
        # mail automation call or the first voice use from inside the
        # packaged app -- no prompt, no error naming the cause, just a
        # failure that looks like a Keep bug. The unbundled pip/venv path
        # never hit this because there's no bundle Info.plist for TCC to
        # read a missing string from in the first place.
        "NSAppleEventsUsageDescription": (
            "Keep uses Apple events to create calendar events and "
            "reminders, and draft email, on your behalf."
        ),
        "NSMicrophoneUsageDescription": (
            "Keep uses the microphone so you can ask it questions by voice."
        ),
        "NSSpeechRecognitionUsageDescription": (
            "Keep uses on-device speech recognition to transcribe what you "
            "say when asking by voice."
        ),
    },
    "packages": sorted({
        "keep",
        "rumps",
        "langchain_apple_foundation_models",
        # py2app's automatic dependency scan never bundled this package's
        # libfoundation_models.dylib -- the compiled extension's embedded
        # rpath points at the wheel-builder's CI directory, not
        # @loader_path, so the scanner can't resolve where to copy it from.
        # Reproduced live: the shipped .app crashed on the first question
        # with a dyld "Library not loaded" error, launch itself was fine.
        # Listing the whole package here bundles its directory verbatim
        # (dylib included) instead of relying on that broken resolution.
        "applefoundationmodels",
        # Every other package with a compiled .so anywhere inside it (found
        # applefoundationmodels' own dylib this way originally, then
        # pydantic_core the same class of bug one rebuild later -- see
        # _packages_with_native_extensions' docstring for why this is now
        # scanned rather than extended one crash at a time).
        *_packages_with_native_extensions(),
    }),
    "includes": [
        # applefoundationmodels/session.py imports this; py2app's automatic
        # scan doesn't follow imports inside a package forced in via
        # "packages" above (that copies the directory verbatim, unscanned),
        # so this transitive dependency was silently missing until the
        # question-answering build check (see build_app.sh) caught it with
        # a real ModuleNotFoundError on first rebuild after adding
        # applefoundationmodels to "packages". Pure-Python (no .so), so
        # unlike the mypyc sibling above, being zipped under "includes" is
        # completely fine -- zipimport works for plain .py/.pyc.
        "typing_extensions",
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
