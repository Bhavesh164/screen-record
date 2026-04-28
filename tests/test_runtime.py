from __future__ import annotations

from pathlib import Path

from screen_record.runtime import bundled_ffmpeg_path


def test_bundled_ffmpeg_path_prefers_executable_directory(tmp_path: Path) -> None:
    executable = tmp_path / "ScreenRecord"
    executable.write_text("", encoding="utf-8")
    executable.chmod(0o755)

    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.write_text("", encoding="utf-8")
    ffmpeg.chmod(0o755)

    assert bundled_ffmpeg_path(executable_path=executable, meipass_path=tmp_path / "ignored") == str(ffmpeg)


def test_bundled_ffmpeg_path_finds_macos_frameworks_binary(tmp_path: Path) -> None:
    executable = tmp_path / "ScreenRecord.app" / "Contents" / "MacOS" / "ScreenRecord"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    executable.chmod(0o755)

    ffmpeg = tmp_path / "ScreenRecord.app" / "Contents" / "Frameworks" / "ffmpeg"
    ffmpeg.parent.mkdir(parents=True)
    ffmpeg.write_text("", encoding="utf-8")
    ffmpeg.chmod(0o755)

    assert bundled_ffmpeg_path(executable_path=executable, meipass_path=tmp_path / "ignored") == str(ffmpeg)
