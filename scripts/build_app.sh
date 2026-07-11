#!/bin/bash
# Builds the unsigned Keep.app bundle and zips it for a GitHub Release.
#
# Unsigned deliberately -- no Apple Developer Program account yet (see
# README's first-run notes). Version comes from src/keep/__init__.py via
# setup.py, never a literal here -- run check_version.py after building to
# confirm pyproject/__init__.py/the built plist all agree before shipping.
#
# py2app refuses to run at all if setuptools has populated
# Distribution.install_requires (build_app.py: "install_requires is no
# longer supported") -- and since pyproject.toml's [project] table has a
# static (non-dynamic) `dependencies` list, setuptools auto-derives
# install_requires from it and setup.py's own kwargs can't override that,
# even an explicit empty list (verified directly, not assumed). The
# practical fix real py2app-plus-pyproject.toml projects use: py2app itself
# only needs setup.py + its OPTIONS dict, not pyproject.toml, so pyproject.toml
# is moved aside for just the py2app invocation and restored immediately
# after via a trap, success or failure.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf build dist

trap 'if [ -f pyproject.toml.build-bak ]; then mv pyproject.toml.build-bak pyproject.toml; fi' EXIT
mv pyproject.toml pyproject.toml.build-bak
python3 setup.py py2app
mv pyproject.toml.build-bak pyproject.toml

python3 scripts/check_version.py

# A successful py2app build is not the same as a working app -- shipped
# v0.1.0's first build passed check_version.py and looked fine, but crashed
# on every launch with a ModuleNotFoundError from a missing compiled
# dependency (charset_normalizer's mypyc runtime module, invisible to
# py2app's automatic dependency scan -- see setup.py's
# _mypyc_runtime_includes() comment) that only a real launch attempt would
# have caught. Never skip this step, even when only chasing a version bump.
echo "Verifying the built app actually launches..."
dist/Keep.app/Contents/MacOS/Keep > /tmp/keep-build-launch-check.log 2>&1 &
LAUNCH_PID=$!
sleep 4
if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "BUILD FAILED: the app crashed on launch. Output:" >&2
    cat /tmp/keep-build-launch-check.log >&2
    exit 1
fi
kill -TERM "$LAUNCH_PID"
rm -f /tmp/keep-build-launch-check.log
echo "Launch check passed."

VERSION=$(python3 -c "import re; print(re.search(r'__version__ = \"([^\"]+)\"', open('src/keep/__init__.py').read()).group(1))")
cd dist
zip -r -q "Keep-${VERSION}-macos.zip" "Keep.app"
cd ..

echo "Built dist/Keep.app and dist/Keep-${VERSION}-macos.zip"
