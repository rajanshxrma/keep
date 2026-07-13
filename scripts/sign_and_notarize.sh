#!/bin/bash
# Signs and notarizes dist/Keep.app with a Developer ID Application
# certificate, so macOS Gatekeeper stops showing "Keep is damaged and
# can't be opened" for people who download the release zip.
#
# This does NOT publish anything new -- Keep is already public
# (github.com/rajanshxrma/keep, released). It only removes friction on an
# already-public download.
#
# Prerequisites, one-time, not automatable (real account/identity actions):
#   1. A "Developer ID Application" certificate in this Mac's login
#      keychain. Xcode -> Settings -> Accounts -> select your Apple ID ->
#      Manage Certificates... -> "+" -> Developer ID Application.
#      (As of writing, `security find-identity -v -p codesigning` only
#      shows an "Apple Development" identity -- that one is for
#      device/simulator debugging, NOT what notarization needs.)
#   2. Notarization credentials stored under a keychain profile:
#        xcrun notarytool store-credentials "keep-notary" \
#          --apple-id "<your Apple ID email>" \
#          --team-id "58Q76NHADF" \
#          --password "<an app-specific password from appleid.apple.com>"
#      (App-specific password, not your regular Apple ID password --
#      generate one at appleid.apple.com under Sign-In and Security.)
#
# Entitlements in Keep.entitlements are a best-effort inference from what
# Keep actually does (Apple Events automation, mic input, bundled
# third-party compiled dependencies) -- NOT yet verified against a real
# signed build, because no cert/notary credentials existed at the time
# this script was written. Run scripts/build_app.sh first if dist/Keep.app
# is missing or stale, then run this, then MANUALLY re-verify (with a
# person watching, not just launch-and-wait) that:
#   - the app still launches and answers a question (voice + typed)
#   - a calendar/reminder/mail automation call still works (this is the
#     one most likely to silently break if an entitlement is wrong --
#     TCC failures here don't always throw a visible error)
# before trusting a signed build to replace the current unsigned release.
set -euo pipefail
cd "$(dirname "$0")/.."

APP_PATH="dist/Keep.app"
ENTITLEMENTS="scripts/Keep.entitlements"
NOTARY_PROFILE="${1:-keep-notary}"

if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: $APP_PATH not found. Run scripts/build_app.sh first." >&2
    exit 1
fi

SIGN_IDENTITY=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | sed -E 's/.*"(.*)"/\1/') || true
if [ -z "$SIGN_IDENTITY" ]; then
    echo "ERROR: no 'Developer ID Application' identity found in the login keychain." >&2
    echo "See the prerequisites comment at the top of this script." >&2
    exit 1
fi
echo "Signing with: $SIGN_IDENTITY"

echo "Codesigning (deep, hardened runtime, secure timestamp)..."
codesign --force --deep --options runtime --timestamp \
    --entitlements "$ENTITLEMENTS" \
    --sign "$SIGN_IDENTITY" \
    "$APP_PATH"

echo "Verifying signature..."
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

VERSION=$(python3 -c "import re; print(re.search(r'__version__ = \"([^\"]+)\"', open('src/keep/__init__.py').read()).group(1))")
ZIP_PATH="dist/Keep-${VERSION}-macos-signed.zip"
echo "Zipping for notarization submission..."
(cd dist && zip -r -q "Keep-${VERSION}-macos-signed.zip" "Keep.app")

echo "Submitting to Apple's notary service (this can take a few minutes)..."
xcrun notarytool submit "$ZIP_PATH" --keychain-profile "$NOTARY_PROFILE" --wait

echo "Stapling the notarization ticket..."
xcrun stapler staple "$APP_PATH"

echo "Verifying Gatekeeper acceptance..."
spctl -a -vvv --type execute "$APP_PATH"

# Re-zip after stapling -- the ticket must be inside the shipped bundle,
# and the pre-staple zip above was only for notarytool's submission.
rm -f "$ZIP_PATH"
(cd dist && zip -r -q "Keep-${VERSION}-macos-signed.zip" "Keep.app")

echo ""
echo "Done: $ZIP_PATH is signed, notarized, and stapled."
echo "Before replacing the GitHub release asset: re-verify launch + a"
echo "calendar/mail automation call + voice, per this script's header comment."
