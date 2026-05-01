from __future__ import annotations

import platform
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from screen_record.models import CaptureRegion, SessionPaths


def create_session_paths(save_dir: Path, capture_keystrokes: bool) -> SessionPaths:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    directory = save_dir / f"screen-record-{stamp}"
    directory.mkdir(parents=True, exist_ok=True)
    if capture_keystrokes:
        return SessionPaths(
            directory=directory,
            source_video=directory / "without_keystrokes.mp4",
            final_video=directory / "with_keystrokes.mp4",
            timeline_file=directory / "timeline.json",
        )
    return SessionPaths(
        directory=directory,
        source_video=directory / "recording.mp4",
        final_video=directory / "recording.mp4",
        timeline_file=directory / "timeline.json",
    )


@dataclass(slots=True)
class SessionMetadata:
    started_at: str
    duration_ms: int
    fps: int
    width: int
    height: int
    monitor: str
    region: dict[str, int] | None
    platform: str

    @classmethod
    def build(
        cls,
        *,
        duration_ms: int,
        fps: int,
        width: int,
        height: int,
        monitor: str,
        region: CaptureRegion | None,
        started_at: datetime,
    ) -> "SessionMetadata":
        return cls(
            started_at=started_at.isoformat(),
            duration_ms=duration_ms,
            fps=fps,
            width=width,
            height=height,
            monitor=monitor,
            region=region.to_dict() if region else None,
            platform=platform.platform(),
        )
