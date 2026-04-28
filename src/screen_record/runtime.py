from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundled_ffmpeg_path(
    *,
    executable_path: str | Path | None = None,
    meipass_path: str | Path | None = None,
) -> str | None:
    executable = Path(executable_path) if executable_path is not None else Path(sys.executable)
    meipass = Path(meipass_path) if meipass_path is not None else Path(getattr(sys, "_MEIPASS", executable.parent))
    names = ["ffmpeg.exe", "ffmpeg"] if os.name == "nt" else ["ffmpeg", "ffmpeg.exe"]

    roots = [executable.parent, meipass]
    macos_frameworks = executable.parent.parent / "Frameworks"
    if macos_frameworks not in roots:
        roots.append(macos_frameworks)

    candidates: list[Path] = []
    for root in roots:
        for name in names:
            candidates.append(root / name)
            candidates.append(root / "bin" / name)

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None
