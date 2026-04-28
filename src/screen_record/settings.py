from __future__ import annotations

import os
import shutil
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

from screen_record.models import AppSettings
from screen_record.runtime import bundled_ffmpeg_path


ORG_NAME = "Kilo"
APP_NAME = "ScreenRecord"


def default_downloads_dir() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    if location:
        return Path(location)
    return Path.home() / "Downloads"


class SettingsStore:
    def __init__(self) -> None:
        self._settings = QSettings(ORG_NAME, APP_NAME)

    def load(self) -> AppSettings:
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
