from __future__ import annotations

import logging
import platform
import threading
from collections import deque
from dataclasses import dataclass, field
from time import monotonic, monotonic_ns
from typing import Any

from screen_record.models import KeyEvent, PauseSpan, TimelineSegment

logger = logging.getLogger(__name__)

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

_MACOS_QUARTZ_AVAILABLE = False
if platform.system() == "Darwin":
    try:
        from Quartz import (
            CGEventTapCreate,
            CGEventTapEnable,
            CGEventGetIntegerValueField,
            CGEventGetFlags,
            CFMachPortCreateRunLoopSource,
            CFRunLoopAddSource,
            CFRunLoopGetCurrent,
            CFRunLoopRun,
            CFRunLoopStop,
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            kCGEventKeyDown,
            kCGEventFlagsChanged,
            kCGKeyboardEventKeycode,
            kCFAllocatorDefault,
            kCFRunLoopDefaultMode,
            kCGEventFlagMaskCommand,
            kCGEventFlagMaskShift,
            kCGEventFlagMaskAlternate,
            kCGEventFlagMaskControl,
            kCGEventFlagMaskAlphaShift,
            kCGEventTapDisabledByTimeout,
            kCGEventTapDisabledByUserInput,
        )
        _MACOS_QUARTZ_AVAILABLE = True
    except ImportError:
        pass

_MACOS_KEYCODE_MAP: dict[int, str] = {
    0x00: "a", 0x01: "s", 0x02: "d", 0x03: "f",
    0x04: "h", 0x05: "g", 0x06: "z", 0x07: "x",
    0x08: "c", 0x09: "v", 0x0B: "b", 0x0C: "q",
    0x0D: "w", 0x0E: "e", 0x0F: "r",
    0x10: "y", 0x11: "t", 0x12: "1", 0x13: "2",
    0x14: "3", 0x15: "4", 0x16: "6", 0x17: "5",
    0x18: "=", 0x19: "9", 0x1A: "7", 0x1B: "-",
    0x1C: "8", 0x1D: "0", 0x1E: "]", 0x1F: "o",
    0x20: "u", 0x21: "[", 0x22: "i", 0x23: "p",
    0x24: "enter", 0x25: "l", 0x26: "j", 0x27: "'",
    0x28: "k", 0x29: ";", 0x2A: "\\", 0x2B: ",",
    0x2C: "/", 0x2D: "n", 0x2E: "m", 0x2F: ".",
    0x30: "tab", 0x31: "space", 0x32: "`",
    0x33: "backspace",
    0x35: "esc",
    0x36: "cmd", 0x37: "cmd",
    0x38: "shift", 0x39: "caps_lock",
    0x3A: "alt", 0x3B: "ctrl",
    0x3C: "shift", 0x3D: "alt", 0x3E: "ctrl",
    0x3F: "fn",
    0x40: "f17",
    0x48: "volume_up", 0x49: "volume_down", 0x4A: "mute",
    0x4C: "kp_enter",
    0x4E: "f19",
    0x60: "f5", 0x61: "f6", 0x62: "f7", 0x63: "f3",
    0x64: "f8", 0x65: "f9", 0x67: "f11",
    0x69: "f13", 0x6B: "f14",
    0x71: "f12", 0x72: "f15",
    0x73: "home", 0x74: "page_up",
    0x75: "delete", 0x76: "f4",
    0x77: "end", 0x78: "f2", 0x79: "page_down",
    0x7A: "f1", 0x7B: "left", 0x7C: "right",
    0x7D: "down", 0x7E: "up",
}

_MACOS_MODIFIER_KEYCODES: set[int] = {
    0x36, 0x37, 0x38, 0x3C,
    0x39,
    0x3A, 0x3D,
    0x3B, 0x3E,
    0x3F,
}

_MACOS_KEYCODE_TO_FLAG: dict[int, int] = {}
if _MACOS_QUARTZ_AVAILABLE:
    _MACOS_KEYCODE_TO_FLAG = {
        0x38: kCGEventFlagMaskShift,
        0x3C: kCGEventFlagMaskShift,
        0x3B: kCGEventFlagMaskControl,
        0x3E: kCGEventFlagMaskControl,
        0x3A: kCGEventFlagMaskAlternate,
        0x3D: kCGEventFlagMaskAlternate,
        0x36: kCGEventFlagMaskCommand,
        0x37: kCGEventFlagMaskCommand,
        0x39: kCGEventFlagMaskAlphaShift,
    }

_MACOS_MODIFIER_DISPLAY: dict[str, str] = {
    "shift": "Shift",
    "ctrl": "Ctrl",
    "alt": "Option",
    "cmd": "Cmd",
    "caps_lock": "Caps Lock",
    "fn": "Fn",
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
            current_text_parts.append(event.display_text)
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
    _listener: Any = None
    _session_start: float = 0.0
    _paused: bool = False
    _pause_spans: list[PauseSpan] = field(default_factory=list)
    _pause_started_ms: int | None = None
    _platform_capture_supported: bool = True
    _macos_tap_ref: Any = None
    _macos_source_ref: Any = None
    _macos_rl_ref: Any = None
    _macos_thread_ref: threading.Thread | None = None
    _macos_ready: threading.Event = field(default_factory=threading.Event)
    _using_macos_tap: bool = False
    _raw_queue: deque = field(default_factory=deque)
    _processor_thread: threading.Thread | None = None
    _processor_stop: threading.Event = field(default_factory=threading.Event)

    def start(self) -> None:
        self._session_start = monotonic()
        self._using_macos_tap = False

        if platform.system() == "Darwin" and _MACOS_QUARTZ_AVAILABLE:
            if self._start_macos():
                self._using_macos_tap = True
                self._processor_stop.clear()
                self._processor_thread = threading.Thread(target=self._process_raw_events, daemon=True)
                self._processor_thread.start()
                return

        self._start_pynput()

    def _start_pynput(self) -> None:
        try:
            from pynput import keyboard

            self._listener = keyboard.Listener(on_press=self._on_press)
            self._listener.start()
        except Exception as exc:
            logger.info("Keyboard capture disabled: %s", exc)
            self._listener = None
            self._platform_capture_supported = False

    def _process_raw_events(self) -> None:
        while not self._processor_stop.is_set():
            try:
                raw = self._raw_queue.popleft()
            except IndexError:
                self._processor_stop.wait(0.005)
                continue
            self._convert_raw_event(raw)

    def _convert_raw_event(self, raw: tuple) -> None:
        event_type, keycode, flags, timestamp_ns = raw
        session_start_ns = int(self._session_start * 1_000_000_000)
        timestamp_ms = (timestamp_ns - session_start_ns) // 1_000_000

        key_name = _MACOS_KEYCODE_MAP.get(keycode)
        if key_name is None:
            return

        is_modifier = keycode in _MACOS_MODIFIER_KEYCODES

        if event_type == 1 and is_modifier:
            expected_flag = _MACOS_KEYCODE_TO_FLAG.get(keycode)
            if expected_flag is not None and not (flags & expected_flag) and keycode != 0x39:
                return

        if is_modifier:
            display_text = _MACOS_MODIFIER_DISPLAY.get(key_name, key_name.title())
        elif key_name in SPECIAL_KEY_NAMES:
            display_text = SPECIAL_KEY_NAMES[key_name]
        elif len(key_name) == 1 and key_name.isalpha():
            if flags & (kCGEventFlagMaskShift | kCGEventFlagMaskAlphaShift):
                display_text = key_name.upper()
            else:
                display_text = key_name
        elif len(key_name) == 1:
            display_text = key_name
        else:
            display_text = key_name.replace("_", " ").title()

        evt = KeyEvent(
            timestamp_ms=timestamp_ms,
            key_text=key_name,
            display_text=display_text,
            is_modifier=is_modifier,
        )
        with self._lock:
            self._events.append(evt)

    def _start_macos(self) -> bool:
        if not _MACOS_QUARTZ_AVAILABLE:
            return False

        events_of_interest = (1 << kCGEventKeyDown) | (1 << kCGEventFlagsChanged)
        raw_queue = self._raw_queue
        session_start_ns_holder = [0]

        def _macos_callback(proxy, event_type, event, refcon):
            if event_type == kCGEventTapDisabledByTimeout:
                tap = collector._macos_tap_ref
                if tap is not None:
                    try:
                        CGEventTapEnable(tap, True)
                    except Exception:
                        pass
                return event
            if event_type == kCGEventTapDisabledByUserInput:
                return event
            if event_type not in (kCGEventKeyDown, kCGEventFlagsChanged):
                return event

            if collector._paused:
                return event

            try:
                keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                flags = CGEventGetFlags(event)
                if keycode in _MACOS_KEYCODE_MAP:
                    raw_queue.append((int(event_type), int(keycode), int(flags), monotonic_ns()))
            except Exception:
                pass

            return event

        collector = self

        try:
            tap = CGEventTapCreate(
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionListenOnly,
                events_of_interest,
                _macos_callback,
                None,
            )
            if tap is None:
                logger.info("macOS keyboard capture: accessibility permission not granted")
                self._platform_capture_supported = False
                return False

            source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)

            self._macos_tap_ref = tap
            self._macos_source_ref = source
            self._macos_ready.clear()
            self._macos_thread_ref = threading.Thread(target=self._run_macos_loop, daemon=True)
            self._macos_thread_ref.start()
            self._macos_ready.wait(timeout=5.0)

            if not self._platform_capture_supported:
                logger.info("macOS keyboard capture failed to start on run loop thread")
                return False

            self._platform_capture_supported = True
            logger.info("macOS keyboard capture started via CGEventTap (dedicated thread)")
            return True
        except Exception as exc:
            logger.info("macOS keyboard capture failed: %s", exc)
            self._platform_capture_supported = False
            return False

    def _run_macos_loop(self) -> None:
        run_loop = CFRunLoopGetCurrent()
        self._macos_rl_ref = run_loop
        try:
            CGEventTapEnable(self._macos_tap_ref, True)
            CFRunLoopAddSource(run_loop, self._macos_source_ref, kCFRunLoopDefaultMode)
            self._macos_ready.set()
            CFRunLoopRun()
        except Exception as exc:
            logger.info("macOS keyboard tap run loop error: %s", exc)
            self._platform_capture_supported = False
            self._macos_ready.set()

    def stop(self) -> None:
        if self._using_macos_tap:
            self._stop_macos()
            self._processor_stop.set()
            if self._processor_thread is not None:
                self._processor_thread.join(timeout=2.0)
                self._processor_thread = None
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _stop_macos(self) -> None:
        if self._macos_rl_ref is not None:
            try:
                CFRunLoopStop(self._macos_rl_ref)
            except Exception:
                pass
            self._macos_rl_ref = None
        if self._macos_thread_ref is not None:
            self._macos_thread_ref.join(timeout=3.0)
            self._macos_thread_ref = None
        if self._macos_tap_ref is not None:
            try:
                CGEventTapEnable(self._macos_tap_ref, False)
            except Exception:
                pass
            self._macos_tap_ref = None
        self._macos_source_ref = None
        self._using_macos_tap = False

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

    def using_macos_tap(self) -> bool:
        return self._using_macos_tap

    def _on_press(self, key: Any) -> None:
        if self._paused:
            return
        try:
            key_text, display_text, is_modifier = normalize_key(key)
            event = KeyEvent(
                timestamp_ms=int((monotonic() - self._session_start) * 1000),
                key_text=key_text,
                display_text=display_text,
                is_modifier=is_modifier,
            )
            with self._lock:
                self._events.append(event)
        except Exception:
            pass