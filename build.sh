#!/bin/zsh
# Builds Mimo.app for macOS.
set -euo pipefail
cd "$(dirname "$0")"
APP="Mimo.app"
CONF="${1:-release}"

echo "==> building Mimo ($CONF)"
swift build -c "$CONF" --disable-sandbox --product MimoApp
BIN="$(swift build -c "$CONF" --show-bin-path)/MimoApp"
[[ -x "$BIN" ]] || { echo "executable not found: $BIN"; exit 1; }

echo "==> assembling the bundle"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/Mimo"
cp Resources/Info.plist "$APP/Contents/Info.plist"
if [[ -f Resources/Mimo.icns ]]; then
    cp Resources/Mimo.icns "$APP/Contents/Resources/Mimo.icns"
fi
printf 'APPL????' > "$APP/Contents/PkgInfo"

echo "==> ad-hoc signing"
codesign --force --sign - "$APP" 2>/dev/null || \
    echo "   (signing failed: the app still starts if you right-click > Open the first time)"

echo "==> done: $(pwd)/$APP"
