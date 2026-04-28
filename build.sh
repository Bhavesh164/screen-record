#!/usr/bin/env bash
# build.sh — Build ScreenRecord standalone executables for the current platform.
# Usage: ./build.sh
#
# On macOS  → produces dist/ScreenRecord.app and dist/ScreenRecord.dmg
# On Linux  → produces dist/ScreenRecord/
# On Windows (via Git Bash / WSL) → produces dist/ScreenRecord/

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

echo "==> Building ScreenRecord with PyInstaller..."
SCREEN_RECORD_FFMPEG_BIN="$FFMPEG_BIN" uv run pyinstaller ScreenRecord.spec --clean --noconfirm

if [[ "$(uname -s)" == "Darwin" ]]; then
    APP_PATH="dist/ScreenRecord.app"
    DMG_PATH="dist/ScreenRecord.dmg"

    if [[ ! -d "$APP_PATH" ]]; then
        echo "Expected app bundle at $APP_PATH but it was not created." >&2
        exit 1
    fi

    echo "==> Creating macOS disk image..."
    staging_dir="$(mktemp -d)"
    cp -R "$APP_PATH" "$staging_dir/"
    xattr -cr "$staging_dir/ScreenRecord.app"
    codesign --force --deep --sign - "$staging_dir/ScreenRecord.app"
    ln -s /Applications "$staging_dir/Applications"
    hdiutil create \
        -volname "Screen Record" \
        -srcfolder "$staging_dir" \
        -ov \
        -format UDZO \
        "$DMG_PATH" >/dev/null
    rm -rf "$staging_dir"
    rm -rf dist/ScreenRecord
    rm -f dist/.DS_Store
fi

echo ""
echo "==> Build complete!"
echo "    Output: dist/"
ls -la dist/
echo ""

case "$(uname -s)" in
    Darwin)
        echo "    macOS app bundle: dist/ScreenRecord.app"
        echo "    Disk image:       dist/ScreenRecord.dmg"
        ;;
    Linux)
        echo "    Directory build:  dist/ScreenRecord/"
        echo "    Run with:         ./dist/ScreenRecord/ScreenRecord"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        echo "    Directory build:  dist\\ScreenRecord\\"
        echo "    Run with:         dist\\ScreenRecord\\ScreenRecord.exe"
        ;;
esac
