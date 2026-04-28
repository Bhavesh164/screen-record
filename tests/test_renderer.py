from __future__ import annotations

import subprocess
from pathlib import Path

from screen_record.models import TimelineSegment
from screen_record.render.ffmpeg_renderer import render_final_video


def test_renderer_creates_output_video(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    final = tmp_path / "final.mp4"
    ffmpeg = "ffmpeg"

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x180:d=1",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    render_final_video(
        ffmpeg_path=ffmpeg,
        source_video=source,
        final_video=final,
        width=320,
        height=180,
        style={"font_name": "DejaVuSans.ttf", "font_size": 18},
        segments=[TimelineSegment(start_ms=0, end_ms=800, text="hello", keys=["h", "e", "l", "l", "o"])],
        work_dir=tmp_path,
    )

    assert final.exists()
    assert final.stat().st_size > 0
