#!/bin/bash
# Builds the native image-narration helper against the beta SDK -- only
# works if Xcode-beta.app is installed (macOS 27 / FoundationModels image
# input isn't in the stable SDK). This is optional infrastructure: if this
# script was never run, NativeImageBackend simply isn't available and
# lantern automatically falls back to VisionOCRBackend -- see backends.py.
set -euo pipefail
cd "$(dirname "$0")"

BETA_DEVELOPER_DIR="/Applications/Xcode-beta.app/Contents/Developer"
if [ ! -d "$BETA_DEVELOPER_DIR" ]; then
    echo "Xcode-beta.app not found -- native backend requires the macOS 27 beta SDK." >&2
    exit 1
fi

DEVELOPER_DIR="$BETA_DEVELOPER_DIR" swift build -c release

mkdir -p bin
cp .build/out/Products/Release/lantern-native-describe bin/lantern-native-describe
echo "Built native/bin/lantern-native-describe"
