from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from screen_record.capture.keystrokes import build_segments
from screen_record.capture.session import SessionMetadata
from screen_record.models import KeyEvent, PauseSpan, TimelineSegment


DEFAULT_STYLE = {
    "overlay_position": "bottom_center",
    "font_name": "HelveticaNeue.ttc",
    "font_size": 36,
    "text_color": "#F5F7FA",
    "card_fill": "#0F172A",
    "card_outline": "#1E293B",
    "group_padding": 18,
    "group_v_padding": 16,
    "key_fill": "#1E293B",
    "key_outline": "#334155",
    "key_pill_h_padding": 20,
    "key_pill_v_padding": 14,
    "key_pill_radius": 12,
    "key_gap": 12,
    "modifier_fill": "#2D5A3D",
    "modifier_outline": "#4ADE80",
    "modifier_text_color": "#BBF7D0",
    "margin_bottom": 90,
    "fade_ms": 120,
}


def build_timeline_payload(
    *,
    session: SessionMetadata,
    events: list[KeyEvent],
    keystroke_count: int,
    pause_spans: list[PauseSpan],
) -> dict[str, Any]:
    segments = build_segments(events)
    return {
        "session": {
            "started_at": session.started_at,
            "duration_ms": session.duration_ms,
            "fps": session.fps,
            "resolution": {"width": session.width, "height": session.height},
            "monitor": session.monitor,
            "region": session.region,
            "platform": session.platform,
        },
        "style": DEFAULT_STYLE.copy(),
        "segments": [segment.to_dict() for segment in segments],
        "stats": {
            "total_keystrokes": keystroke_count,
            "pause_spans": [span.to_dict() for span in pause_spans],
        },
    }


def write_timeline(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_timeline(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def coerce_segments(payload: dict[str, Any]) -> list[TimelineSegment]:
    return [
        TimelineSegment(
            start_ms=int(segment["start_ms"]),
            end_ms=int(segment["end_ms"]),
            text=str(segment["text"]),
            keys=list(segment.get("keys", [])),
            visible=bool(segment.get("visible", True)),
        )
        for segment in payload.get("segments", [])
    ]
