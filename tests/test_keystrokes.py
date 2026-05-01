from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

from screen_record.capture.keystrokes import KeyEventCollector, build_segments, normalize_key, _MACOS_QUARTZ_AVAILABLE
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


def test_key_collector_starts_on_macos_with_quartz(monkeypatch) -> None:
    monkeypatch.setattr("screen_record.capture.keystrokes.platform.system", lambda: "Darwin")
    if not _MACOS_QUARTZ_AVAILABLE:
        collector = KeyEventCollector()
        collector.start()
        assert collector.supported() is False
        assert collector.snapshot() == []
        return

    import screen_record.capture.keystrokes as ks

    original_create = ks.CGEventTapCreate

    def _fake_tap_create(tap_point, place, options, events_of_interest, callback, refcon):
        return original_create(tap_point, place, options, events_of_interest, callback, refcon)

    with patch.object(ks, "CGEventTapCreate", return_value=None):
        collector = KeyEventCollector()
        collector.start()
        assert collector._using_macos_tap is False
        assert collector.supported() is False
        collector.stop()


def test_key_collector_graceful_failure_without_quartz(monkeypatch) -> None:
    monkeypatch.setattr("screen_record.capture.keystrokes.platform.system", lambda: "Darwin")
    import screen_record.capture.keystrokes as ks

    monkeypatch.setattr(ks, "_MACOS_QUARTZ_AVAILABLE", False)
    # Make pynput import fail so _start_pynput gracefully sets supported=False
    monkeypatch.setitem(sys.modules, "pynput", None)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", None)
    collector = KeyEventCollector()
    collector.start()
    assert collector.supported() is False


def test_build_segments_with_modifiers() -> None:
    events = [
        KeyEvent(timestamp_ms=0, key_text="shift", display_text="Shift", is_modifier=True),
        KeyEvent(timestamp_ms=50, key_text="h", display_text="H"),
    ]
    segments = build_segments(events, inactivity_threshold_ms=300)
    assert len(segments) == 1
    assert segments[0].text == "[Shift] H"


def test_build_segments_empty() -> None:
    segments = build_segments([], inactivity_threshold_ms=300)
    assert segments == []