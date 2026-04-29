from __future__ import annotations
import sys
from types import SimpleNamespace

from screen_record.capture.keystrokes import KeyEventCollector, build_segments, normalize_key
from screen_record.models import KeyEvent


def test_normalize_printable_character() -> None:
    key = SimpleNamespace(char="a")
    normalized = normalize_key(key)
    assert normalized == ("a", "a", False)


def test_normalize_special_key() -> None:
    key = SimpleNamespace(name="enter")
    normalized = normalize_key(key)
    assert normalized == ("enter", "Enter", False)


def test_groups_events_by_inactivity() -> None:
    events = [
        KeyEvent(timestamp_ms=0, key_text="h", display_text="h"),
        KeyEvent(timestamp_ms=70, key_text="i", display_text="i"),
        KeyEvent(timestamp_ms=900, key_text="enter", display_text="Enter"),
    ]

    segments = build_segments(events, inactivity_threshold_ms=300)

    assert [segment.text for segment in segments] == ["hi", "[Enter]"]
    assert segments[0].start_ms == 0
    assert segments[1].start_ms == 900

def test_key_collector_graceful_failure_on_macos(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    collector = KeyEventCollector()

    collector.start()

    assert collector.supported() is False
    assert collector.snapshot() == []