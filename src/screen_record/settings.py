from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

from screen_record.models import AppSettings
from screen_record.runtime import bundled_ffmpeg_path


ORG_NAME = "Kilo"
APP_NAME = "CaptoKey"


def _settings_json_path() -> Path:
    return Path.home() / ".config" / "captokey" / "settings.json"


def default_downloads_dir() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    if location:
        return Path(location)
    return Path.home() / "Downloads"


class SettingsStore:
    def __init__(self) -> None:
        self._settings = QSettings(ORG_NAME, APP_NAME)
        self._json_path = _settings_json_path()
        self._json_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppSettings:
        # Prefer JSON file (more reliable with PyInstaller bundles)
        if self._json_path.exists():
            try:
                with open(self._json_path, encoding="utf-8") as f:
                    data = json.load(f)
                return AppSettings(
                    save_dir=str(data.get("save_dir", str(default_downloads_dir()))),
                    capture_mode=str(data.get("capture_mode", "full_display")),
                    target_fps=int(data.get("target_fps", 30)),
                    output_container=str(data.get("output_container", "mp4")),
                    ffmpeg_path=str(data.get("ffmpeg_path", "")),
                )
            except Exception:
                pass

        # Fallback to QSettings
        save_dir = self._settings.value("save_dir", str(default_downloads_dir()))
        capture_mode = self._settings.value("capture_mode", "full_display")
        target_fps = int(self._settings.value("target_fps", 30))
        output_container = self._settings.value("output_container", "mp4")
        ffmpeg_path = self._settings.value("ffmpeg_path", "")
        return AppSettings(
            save_dir=str(save_dir),
            capture_mode=str(capture_mode),
            target_fps=target_fps,
            output_container=str(output_container),
            ffmpeg_path=str(ffmpeg_path),
        )

    def save(self, settings: AppSettings) -> None:
        data = {
            "save_dir": settings.save_dir,
            "capture_mode": settings.capture_mode,
            "target_fps": settings.target_fps,
            "output_container": settings.output_container,
            "ffmpeg_path": settings.ffmpeg_path,
        }
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Also save to QSettings for backward compatibility
        self._settings.setValue("save_dir", settings.save_dir)
        self._settings.setValue("capture_mode", settings.capture_mode)
        self._settings.setValue("target_fps", settings.target_fps)
        self._settings.setValue("output_container", settings.output_container)
        self._settings.setValue("ffmpeg_path", settings.ffmpeg_path)
        self._settings.sync()


def resolve_ffmpeg_path(configured_path: str = "") -> str:
    if configured_path:
        expanded = str(Path(configured_path).expanduser())
        if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
            return expanded
    bundled = bundled_ffmpeg_path()
    if bundled:
        return bundled
    located = shutil.which("ffmpeg")
    if located:
        return located
    raise FileNotFoundError("ffmpeg was not found. Configure it in Settings.")
