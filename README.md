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

## macOS Permissions

CaptoKey requires **Screen Recording** permission on macOS to capture the screen.

**First run:**
1. Click **Record** in CaptoKey
2. macOS will show a system dialog asking for permission
3. Click **Open System Settings** and toggle **CaptoKey** ON
4. **Quit and reopen CaptoKey** completely — the permission only takes effect after a restart

If you rebuild the app (which changes the binary signature), macOS will invalidate the previous permission. In that case:
1. Open **System Settings → Privacy & Security → Screen Recording**
2. **Remove** CaptoKey from the list
3. **Add it back** and toggle it ON
4. Restart CaptoKey

You can also reset the permission from within the app: **Settings → Reset Screen Recording Permission**.

## Build App Bundle

```bash
./build.sh
```

The build script follows the same `uv` + PyInstaller pattern as `picture-clipboard` and copies the current machine's `ffmpeg` binary into the packaged app. To override which binary gets embedded:

```bash
SCREEN_RECORD_FFMPEG_BIN=/absolute/path/to/ffmpeg ./build.sh
```

PyInstaller builds must be created on the target operating system.
