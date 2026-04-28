from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from pynput import keyboard

from screen_record.models import KeyEvent, PauseSpan, TimelineSegment


MODIFIER_KEYS = {"ctrl", "ctrl_l", "ctrl_r", "alt", "alt_l", "alt_r", "shift", "shift_l", "shift_r", "cmd", "cmd_l", "cmd_r"}
SPECIAL_KEY_NAMES = {
    "enter": "Enter",
    "space": "Space",
    "tab": "Tab",
    "backspace": "Backspace",
    "esc": "Esc",
    "delete": "Delete",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
}


def normalize_key(key: Any) -> tuple[str, str, bool]:
    if hasattr(key, "char") and getattr(key, "char"):
        return key.char, key.char, False

    name = getattr(key, "name", str(key)).replace("Key.", "").lower()
    is_modifier = name in MODIFIER_KEYS
    display = SPECIAL_KEY_NAMES.get(name, name.replace("_", " ").title())
    return name, display, is_modifier


def build_segments(events: list[KeyEvent], inactivity_threshold_ms: int = 650) -> list[TimelineSegment]:
    if not events:
        return []

    segments: list[TimelineSegment] = []
    current_keys: list[str] = []
    current_text_parts: list[str] = []
    start_ms = events[0].timestamp_ms
    last_ms = events[0].timestamp_ms

    for event in events:
        if event.timestamp_ms - last_ms > inactivity_threshold_ms and current_keys:
            segments.append(
                TimelineSegment(
                    start_ms=start_ms,
                    end_ms=last_ms + 600,
                    text="".join(current_text_parts).strip() or " ".join(current_keys),
                    keys=current_keys.copy(),
                    visible=True,
                )
            )
            current_keys.clear()
            current_text_parts.clear()
            start_ms = event.timestamp_ms

        current_keys.append(event.display_text)
        if len(event.key_text) == 1 and not event.is_modifier:
            current_text_parts.append(event.key_text)
        elif event.display_text == "Space":
            current_text_parts.append(" ")
        else:
            if current_text_parts and not current_text_parts[-1].endswith(" "):
                current_text_parts.append(" ")
            current_text_parts.append(f"[{event.display_text}] ")
        last_ms = event.timestamp_ms

    if current_keys:
        segments.append(
            TimelineSegment(
                start_ms=start_ms,
                end_ms=last_ms + 600,
                text="".join(current_text_parts).strip() or " ".join(current_keys),
                keys=current_keys.copy(),
                visible=True,
            )
        )
    return segments


@dataclass(slots=True)
class KeyEventCollector:
    _events: deque[KeyEvent] = field(default_factory=deque)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _listener: keyboard.Listener | None = None
    _session_start: float = 0.0
    _paused: bool = False
    _pause_spans: list[PauseSpan] = field(default_factory=list)
    _pause_started_ms: int | None = None
    _platform_capture_supported: bool = True

    def start(self) -> None:
        self._session_start = monotonic()
        try:
            self._listener = keyboard.Listener(on_press=self._on_press)
            self._listener.start()
        except Exception:
            self._platform_capture_supported = False

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def set_paused(self, paused: bool, elapsed_ms: int) -> None:
        self._paused = paused
        if paused and self._pause_started_ms is None:
            self._pause_started_ms = elapsed_ms
        elif not paused and self._pause_started_ms is not None:
            self._pause_spans.append(PauseSpan(self._pause_started_ms, elapsed_ms))
            self._pause_started_ms = None

    def snapshot(self) -> list[KeyEvent]:
        with self._lock:
            return list(self._events)

    def pause_spans(self) -> list[PauseSpan]:
        return list(self._pause_spans)

    def supported(self) -> bool:
        return self._platform_capture_supported

    def _on_press(self, key: Any) -> None:
        if self._paused:
            return
        key_text, display_text, is_modifier = normalize_key(key)
        event = KeyEvent(
            timestamp_ms=int((monotonic() - self._session_start) * 1000),
            key_text=key_text,
            display_text=display_text,
            is_modifier=is_modifier,
        )
        with self._lock:
            self._events.append(event)
