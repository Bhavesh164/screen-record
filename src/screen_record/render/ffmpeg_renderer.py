from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from screen_record.models import TimelineSegment
from screen_record.render.overlay import render_segment_overlay


def render_final_video(
    *,
    ffmpeg_path: str,
    source_video: Path,
    final_video: Path,
    width: int,
    height: int,
    style: dict[str, object],
    segments: list[TimelineSegment],
    work_dir: Path,
) -> None:
    visible_segments = [segment for segment in segments if segment.visible and segment.text.strip()]
    if not visible_segments:
        shutil.copy2(source_video, final_video)
        return

    overlay_paths: list[Path] = []
    inputs = [ffmpeg_path, "-y", "-i", str(source_video)]
    filter_parts: list[str] = []
    previous = "[0:v]"

    for index, segment in enumerate(visible_segments, start=1):
        overlay_path = work_dir / f"overlay-{index:04d}.png"
        render_segment_overlay(
            output_path=overlay_path,
            width=width,
            height=height,
            segment=segment,
            style=style,
        )
        overlay_paths.append(overlay_path)
        inputs.extend(["-loop", "1", "-i", str(overlay_path)])
        output_label = f"[v{index}]"
        start_time = max(0.0, segment.start_ms / 1000.0)
        end_time = max(start_time, segment.end_ms / 1000.0)
        filter_parts.append(
            f"{previous}[{index}:v]overlay=0:0:eof_action=pass:shortest=1:enable='between(t,{start_time:.3f},{end_time:.3f})'{output_label}"
        )
        previous = output_label

    command = [
        *inputs,
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        previous,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(final_video),
    ]
    process = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
    for path in overlay_paths:
        path.unlink(missing_ok=True)
    if process.returncode != 0:
        raise RuntimeError(process.stderr.decode("utf-8", errors="replace"))
