#!/usr/bin/env bash
# build.sh — Build CaptoKey standalone executables for the current platform.
# Usage: ./build.sh
#
# On macOS  → produces dist/CaptoKey.app and dist/CaptoKey.dmg
# On Linux  → produces dist/CaptoKey/
# On Windows (via Git Bash / WSL) → produces dist/CaptoKey/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

FFMPEG_BIN="${SCREEN_RECORD_FFMPEG_BIN:-$(command -v ffmpeg || true)}"
if [[ -z "$FFMPEG_BIN" ]]; then
    echo "ffmpeg was not found on PATH. Install it or set SCREEN_RECORD_FFMPEG_BIN before building." >&2
    exit 1
fi

echo "==> Syncing uv environment..."
uv sync --group dev

echo "==> Cleaning previous build artifacts..."
rm -rf build/ dist/
mkdir -p build/ScreenRecord

echo "==> Building CaptoKey with PyInstaller..."
SCREEN_RECORD_FFMPEG_BIN="$FFMPEG_BIN" uv run pyinstaller ScreenRecord.spec --clean --noconfirm

if [[ "$(uname -s)" == "Darwin" ]]; then
    APP_PATH="dist/CaptoKey.app"
    DMG_PATH="dist/CaptoKey.dmg"

    if [[ ! -d "$APP_PATH" ]]; then
        echo "Expected app bundle at $APP_PATH but it was not created." >&2
        exit 1
    fi

    echo "==> Creating macOS disk image..."
    staging_dir="$(mktemp -d)"
    cp -R "$APP_PATH" "$staging_dir/"
    xattr -cr "$staging_dir/CaptoKey.app"
    codesign --force --deep --sign - --entitlements macos/CaptoKey.entitlements "$staging_dir/CaptoKey.app"
    ln -s /Applications "$staging_dir/Applications"
    hdiutil create \
        -volname "CaptoKey" \
        -srcfolder "$staging_dir" \
        -ov \
        -format UDZO \
        "$DMG_PATH" >/dev/null
    rm -rf "$staging_dir"
    rm -rf dist/CaptoKey
    rm -f dist/.DS_Store
fi

echo ""
echo "==> Build complete!"
echo "    Output: dist/"
ls -la dist/
echo ""

case "$(uname -s)" in
    Darwin)
        echo "    macOS app bundle: dist/CaptoKey.app"
        echo "    Disk image:       dist/CaptoKey.dmg"
        ;;
    Linux)
        echo "    Directory build:  dist/CaptoKey/"
        echo "    Run with:         ./dist/CaptoKey/CaptoKey"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        echo "    Directory build:  dist\\CaptoKey\\"
        echo "    Run with:         dist\\CaptoKey\\CaptoKey.exe"
        ;;
esac
