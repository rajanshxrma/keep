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

VERSION=$(python3 -c "import re; print(re.search(r'__version__ = \"([^\"]+)\"', open('src/keep/__init__.py').read()).group(1))")
cd dist
zip -r -q "Keep-${VERSION}-macos.zip" "Keep.app"
cd ..

echo "Built dist/Keep.app and dist/Keep-${VERSION}-macos.zip"
