from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FFmpegVideoWriter:
    ffmpeg_path: str
    output_path: Path
    width: int
    height: int
    fps: int
    _process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        command = [
            self.ffmpeg_path,
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgra",
            "-s",
            f"{self.width}x{self.height}",
            "-r",
            str(self.fps),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(self.output_path),
        ]
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    def write_frame(self, frame_bytes: bytes) -> None:
        if not self._process or not self._process.stdin:
            raise RuntimeError("ffmpeg process is not started")
        self._process.stdin.write(frame_bytes)

    def stop(self) -> None:
        if not self._process:
            return
        stderr = b""
        if self._process.stdin:
            self._process.stdin.close()
        if self._process.stderr:
            stderr = self._process.stderr.read()
            self._process.stderr.close()
        return_code = self._process.wait()
        self._process = None
        if return_code != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="replace"))
