# CaptoKey

Desktop screen recorder built with PySide6, `mss`, `pynput`, Pillow, `ffmpeg`, and macOS `Quartz` CGEventTap.

## Features

- Floating recorder HUD with timer, stats, pause/stop/settings controls
- Full-display or selected-region capture
- Single final video output (`final.mp4`) with keystroke overlays
- Editable `timeline.json` capturing every key press with timestamps
- Deterministic final-video rerender with keystroke overlays
- macOS keyboard capture via Quartz CGEventTap (no pynput crashes)
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

CaptoKey requires **Screen Recording** permission on macOS to capture the screen, and **Accessibility** permission to capture keystrokes.

### Screen Recording

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

### Accessibility (Keyboard Capture)

CaptoKey uses a **Quartz CGEventTap** to capture keystrokes for the on-screen overlay. This requires Accessibility permission:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Toggle **CaptoKey** ON (or add it if not listed)
3. Restart CaptoKey

Without this permission, the app will still record the screen and produce a video, but keystroke overlays will not appear. Keystrokes are captured as `listen-only` events — they are observed, not intercepted or modified.

## Output

Each recording session creates a folder (e.g. `screen-record-20260502-143055/`) containing:

- **`final.mp4`** — the final video with keystroke overlays burned in
- **`timeline.json`** — editable JSON with every key press, timestamps, and overlay style settings

To rerender with different overlay styles, edit `timeline.json` and click **Render Again** in the completion dialog.

## Build App Bundle

```bash
./build.sh
```

The build script follows the same `uv` + PyInstaller pattern as `picture-clipboard` and copies the current machine's `ffmpeg` binary into the packaged app. To override which binary gets embedded:

```bash
SCREEN_RECORD_FFMPEG_BIN=/absolute/path/to/ffmpeg ./build.sh
```

PyInstaller builds must be created on the target operating system.
