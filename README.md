# CaptoKey

Desktop screen recorder built with PySide6, `mss`, `pynput`, Pillow, and `ffmpeg`.

## Features

- Floating recorder HUD with timer, stats, pause/stop/settings controls
- Full-display or selected-region capture
- Clean source recording plus editable `timeline.json`
- Deterministic final-video rerender with keystroke overlays
- Cross-platform save directory defaults and persistent settings

## Install

```bash
uv sync
```

For tests and packaging tools:

```bash
uv sync --group dev
```

During development, `ffmpeg` must be available on `PATH`, or its location can be set in the app settings.
Packaged builds bundle `ffmpeg` inside the final app/directory and prefer that copy automatically at runtime.

## Run

```bash
uv run screen-record
```

## Test

```bash
uv run pytest
```

## Build App Bundle

```bash
./build.sh
```

The build script follows the same `uv` + PyInstaller pattern as `picture-clipboard` and copies the current machine's `ffmpeg` binary into the packaged app. To override which binary gets embedded:

```bash
SCREEN_RECORD_FFMPEG_BIN=/absolute/path/to/ffmpeg ./build.sh
```

PyInstaller builds must be created on the target operating system.
