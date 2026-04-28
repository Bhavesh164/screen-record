from __future__ import annotations

from datetime import datetime

from screen_record.capture.session import SessionMetadata
from screen_record.models import CaptureRegion, KeyEvent, PauseSpan
from screen_record.render.timeline import build_timeline_payload


def test_timeline_payload_contains_session_and_stats() -> None:
    session = SessionMetadata.build(
        duration_ms=1400,
        fps=30,
        width=1280,
        height=720,
        monitor="primary",
        region=CaptureRegion(left=10, top=20, width=1280, height=720),
        started_at=datetime(2026, 4, 29, 12, 0, 0),
    )
    payload = build_timeline_payload(
        session=session,
        events=[KeyEvent(timestamp_ms=10, key_text="a", display_text="a")],
        keystroke_count=1,
        pause_spans=[PauseSpan(start_ms=100, end_ms=200)],
    )

    assert payload["session"]["resolution"] == {"width": 1280, "height": 720}
    assert payload["stats"]["total_keystrokes"] == 1
    assert payload["segments"][0]["text"] == "a"
