from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class CaptureRegion:
    left: int
    top: int
    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(slots=True)
class AppSettings:
    save_dir: str
    capture_mode: str = "full_display"
    target_fps: int = 30
    output_container: str = "mp4"
    ffmpeg_path: str = ""
    capture_keystrokes: bool = True

    def resolved_save_dir(self) -> Path:
        return Path(self.save_dir).expanduser()


@dataclass(slots=True)
class KeyEvent:
    timestamp_ms: int
    key_text: str
    display_text: str
    is_modifier: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TimelineSegment:
    start_ms: int
    end_ms: int
    text: str
    keys: list[str] = field(default_factory=list)
    visible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PauseSpan:
    start_ms: int
    end_ms: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(slots=True)
class SessionPaths:
    directory: Path
    source_video: Path
    final_video: Path
    timeline_file: Path


@dataclass(slots=True)
class RecorderStats:
    dropped_frames: int = 0
    keystroke_count: int = 0

