from __future__ import annotations

from pathlib import Path

from screen_record.settings import resolve_ffmpeg_path


def test_resolve_ffmpeg_path_uses_explicit_binary(tmp_path: Path) -> None:
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    ffmpeg.chmod(0o755)

    assert resolve_ffmpeg_path(str(ffmpeg)) == str(ffmpeg)
