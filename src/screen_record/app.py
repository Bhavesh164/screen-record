from __future__ import annotations

import ctypes
import platform
import queue
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon


def _macos_ensure_screen_capture() -> tuple[bool, str | None]:
    """Request/verify macOS screen-recording permission.

    Uses ``CGRequestScreenCaptureAccess`` (macOS 10.15+) which shows the
    system permission dialog when needed.  After the API claims permission
    is granted we do a real ``mss`` test grab to confirm it actually works
    in this process – a restart is sometimes required.

    Returns *(allowed, message)*.  *message* is non-None when permission is
    denied or needs a restart.
    """
    if platform.system() != "Darwin":
        return True, None

    denied_msg = (
        "Screen recording permission is required.\n\n"
        "1. Open System Settings → Privacy & Security → Screen Recording\n"
        "2. Make sure CaptoKey is enabled (toggle ON)\n"
        "3. Restart CaptoKey completely (quit and reopen)\n\n"
        "If you just rebuilt the app, remove CaptoKey from the list, add it again, then restart."
    )

    # 1. Try the modern API first – it shows the system dialog if needed.
    try:
        cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        if hasattr(cg, "CGRequestScreenCaptureAccess"):
            cg.CGRequestScreenCaptureAccess.restype = ctypes.c_bool
            granted = cg.CGRequestScreenCaptureAccess()
            if granted:
                # The API says yes, but macOS often still requires a process
                # restart before CoreGraphics capture APIs actually succeed.
                try:
                    import mss

                    with mss.mss() as sct:
                        sct.grab(sct.monitors[0])
                    return True, None
                except Exception:
                    return (
                        False,
                        (
                            "Screen recording permission was granted, but a restart is required for it to take effect.\n\n"
                            "Please quit CaptoKey completely and reopen it."
                        ),
                    )
            # Explicitly denied by user (or dialog dismissed).
            return False, denied_msg
    except Exception:
        pass

    # 2. Fallback for older macOS – try a direct capture.
    try:
        import mss

        with mss.mss() as sct:
            sct.grab(sct.monitors[0])
        return True, None
    except Exception:
        pass

    return False, denied_msg

from screen_record.capture.ffmpeg import FFmpegVideoWriter
from screen_record.capture.keystrokes import KeyEventCollector
from screen_record.capture.providers import FramePayload, default_region_for_primary_screen, make_capture_provider
from screen_record.capture.session import SessionMetadata, create_session_paths
from screen_record.models import AppSettings, CaptureRegion
from screen_record.render.ffmpeg_renderer import render_final_video
from screen_record.render.timeline import build_timeline_payload, coerce_segments, load_timeline, write_timeline
from screen_record.runtime import asset_path
from screen_record.settings import SettingsStore, resolve_ffmpeg_path
from screen_record.ui.global_hotkeys import GlobalHotkeyManager
from screen_record.ui.main_window import RecorderWindow
from screen_record.ui.region_selector import RegionSelector


class SessionClock:
    def __init__(self) -> None:
        self._started = time.monotonic()
        self._pause_started: float | None = None
        self._paused_total = 0.0

    def set_paused(self, paused: bool) -> None:
        if paused and self._pause_started is None:
            self._pause_started = time.monotonic()
        elif not paused and self._pause_started is not None:
            self._paused_total += time.monotonic() - self._pause_started
            self._pause_started = None

    def elapsed_ms(self) -> int:
        now = self._pause_started if self._pause_started is not None else time.monotonic()
        return int((now - self._started - self._paused_total) * 1000)


@dataclass(slots=True)
class RecorderSnapshot:
    elapsed_ms: int = 0
    file_size_bytes: int = 0
    keystrokes: int = 0
    active: bool = False
    paused: bool = False


class RecorderController(QObject):
    statsUpdated = Signal(int, int, int)
    stateChanged = Signal(bool, bool)
    errorRaised = Signal(str)
    sessionSaved = Signal(str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self._capture_thread: threading.Thread | None = None
        self._writer_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._frame_queue: queue.Queue[FramePayload] = queue.Queue(maxsize=3)
        self._collector = KeyEventCollector()
        self._clock: SessionClock | None = None
        self._writer: FFmpegVideoWriter | None = None
        self._session_paths = None
        self._started_at: datetime | None = None
        self._snapshot = RecorderSnapshot()
        self._snapshot_lock = threading.Lock()
        self._stop_lock = threading.Lock()
        self._stopping = False
        self._failed = False
        self._dropped_frames = 0
        self._active_region: CaptureRegion | None = None

    def start(self, region: CaptureRegion) -> None:
        if self._snapshot.active:
            return

        try:
            # Test grab to determine actual capture dimensions (handles Retina displays)
            test_provider = make_capture_provider(region)
            test_frame = test_provider.grab()
            del test_provider

            ffmpeg_path = resolve_ffmpeg_path(self.settings.ffmpeg_path)
            self.settings.resolved_save_dir().mkdir(parents=True, exist_ok=True)
            self._session_paths = create_session_paths(self.settings.resolved_save_dir())
            self._active_region = region
            self._stop_event.clear()
            self._frame_queue = queue.Queue(maxsize=3)
            self._collector = KeyEventCollector()
            self._collector.start()
            self._clock = SessionClock()
            self._started_at = datetime.now()
            self._dropped_frames = 0
            self._failed = False
            self._stopping = False
            self._writer = FFmpegVideoWriter(
                ffmpeg_path=ffmpeg_path,
                output_path=self._session_paths.source_video,
                width=test_frame.width,
                height=test_frame.height,
                fps=self.settings.target_fps,
            )
            self._writer.start()
        except Exception as exc:
            self._cleanup_after_failed_start()
            msg = str(exc)
            if "CGImage is NULL" in msg or "screen capture" in msg.lower():
                msg = (
                    "Screen recording permission was denied or is not active.\n\n"
                    "1. Open System Settings → Privacy & Security → Screen Recording\n"
                    "2. Make sure CaptoKey is enabled\n"
                    "3. Restart CaptoKey completely (quit and reopen)\n\n"
                    "If you just rebuilt the app, macOS may have invalidated the permission. "
                    "Remove CaptoKey from the list and add it again, then restart."
                )
            raise RuntimeError(msg) from exc

        with self._snapshot_lock:
            self._snapshot = RecorderSnapshot(active=True, paused=False)

        self._capture_thread = threading.Thread(target=self._capture_loop, args=(region,), daemon=True)
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._capture_thread.start()
        self._writer_thread.start()
        self.stateChanged.emit(True, False)

    def toggle_pause(self) -> None:
        if not self._snapshot.active or self._clock is None:
            return
        paused = not self._snapshot.paused
        self._clock.set_paused(paused)
        self._collector.set_paused(paused, self._clock.elapsed_ms())
        with self._snapshot_lock:
            self._snapshot.paused = paused
        self.stateChanged.emit(True, paused)

    def stop(self) -> None:
        if not self._snapshot.active:
            return
        self._request_stop()

    def rerender(self, session_dir: str) -> None:
        threading.Thread(target=self._rerender_worker, args=(session_dir,), daemon=True).start()

    def _stop_worker(self) -> None:
        self._stop_event.set()
        current = threading.current_thread()
        if self._capture_thread and self._capture_thread is not current:
            self._capture_thread.join(timeout=5)
        if self._writer_thread and self._writer_thread is not current:
            self._writer_thread.join(timeout=5)
        self._collector.stop()

        try:
            if self._writer:
                self._writer.stop()
            if not self._failed:
                self._finalize_session()
        except Exception as exc:
            self.errorRaised.emit(str(exc))
        finally:
            with self._snapshot_lock:
                self._snapshot.active = False
                self._snapshot.paused = False
            self._capture_thread = None
            self._writer_thread = None
            self._writer = None
            self._clock = None
            self._stopping = False
            self.stateChanged.emit(False, False)

    def _rerender_worker(self, session_dir: str) -> None:
        session_path = Path(session_dir)
        payload = load_timeline(session_path / "timeline.json")
        resolution = payload["session"]["resolution"]
        render_final_video(
            ffmpeg_path=resolve_ffmpeg_path(self.settings.ffmpeg_path),
            source_video=session_path / "source.mp4",
            final_video=session_path / "final.mp4",
            width=int(resolution["width"]),
            height=int(resolution["height"]),
            style=payload.get("style", {}),
            segments=coerce_segments(payload),
            work_dir=session_path,
        )
        self.sessionSaved.emit(str(session_path))

    def poll(self) -> None:
        with self._snapshot_lock:
            snapshot = RecorderSnapshot(
                elapsed_ms=self._snapshot.elapsed_ms,
                file_size_bytes=self._snapshot.file_size_bytes,
                keystrokes=self._snapshot.keystrokes,
                active=self._snapshot.active,
                paused=self._snapshot.paused,
            )
        self.statsUpdated.emit(snapshot.elapsed_ms, snapshot.file_size_bytes, snapshot.keystrokes)

    def _capture_loop(self, region: CaptureRegion) -> None:
        try:
            provider = make_capture_provider(region)
            frame_interval = 1 / max(1, self.settings.target_fps)
            next_tick = time.monotonic()

            while not self._stop_event.is_set():
                if self._snapshot.paused:
                    time.sleep(0.05)
                    continue

                now = time.monotonic()
                if now < next_tick:
                    time.sleep(next_tick - now)
                    continue

                frame = provider.grab()
                try:
                    self._frame_queue.put_nowait(frame)
                except queue.Full:
                    try:
                        self._frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._frame_queue.put_nowait(frame)
                    self._dropped_frames += 1

                elapsed_ms = self._clock.elapsed_ms() if self._clock else 0
                file_size = self._session_paths.source_video.stat().st_size if self._session_paths and self._session_paths.source_video.exists() else 0
                with self._snapshot_lock:
                    self._snapshot.elapsed_ms = elapsed_ms
                    self._snapshot.file_size_bytes = file_size
                    self._snapshot.keystrokes = len(self._collector.snapshot())
                next_tick += frame_interval
                if next_tick < now - frame_interval:
                    next_tick = now + frame_interval
        except Exception as exc:
            self._fail_recording(str(exc))

    def _writer_loop(self) -> None:
        while not self._stop_event.is_set() or not self._frame_queue.empty():
            try:
                frame = self._frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                if self._writer:
                    self._writer.write_frame(frame.bytes_bgra)
            except Exception as exc:
                self._fail_recording(str(exc))
                return

    def _request_stop(self) -> None:
        with self._stop_lock:
            if self._stopping:
                return
            self._stopping = True
        threading.Thread(target=self._stop_worker, daemon=True).start()

    def _fail_recording(self, message: str) -> None:
        self._failed = True
        self.errorRaised.emit(message)
        self._stop_event.set()
        self._request_stop()

    def _cleanup_after_failed_start(self) -> None:
        self._stop_event.set()
        self._collector.stop()
        if self._writer:
            try:
                self._writer.stop()
            except Exception:
                pass
        self._writer = None
        self._clock = None
        with self._snapshot_lock:
            self._snapshot = RecorderSnapshot()

    def _finalize_session(self) -> None:
        if not self._session_paths or not self._clock or not self._started_at or not self._active_region:
            return

        elapsed_ms = self._clock.elapsed_ms()
        events = self._collector.snapshot()
        session = SessionMetadata.build(
            duration_ms=elapsed_ms,
            fps=self.settings.target_fps,
            width=self._active_region.width,
            height=self._active_region.height,
            monitor="primary",
            region=self._active_region,
            started_at=self._started_at,
        )
        payload = build_timeline_payload(
            session=session,
            events=events,
            keystroke_count=len(events),
            pause_spans=self._collector.pause_spans(),
        )
        payload["stats"]["dropped_frames"] = self._dropped_frames
        write_timeline(self._session_paths.timeline_file, payload)
        render_final_video(
            ffmpeg_path=resolve_ffmpeg_path(self.settings.ffmpeg_path),
            source_video=self._session_paths.source_video,
            final_video=self._session_paths.final_video,
            width=self._active_region.width,
            height=self._active_region.height,
            style=payload.get("style", {}),
            segments=coerce_segments(payload),
            work_dir=self._session_paths.directory,
        )
        self.sessionSaved.emit(str(self._session_paths.directory))


class ScreenRecordApplication(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.controller = RecorderController(self.settings)
        self.window = RecorderWindow(self.settings)
        self.selector = RegionSelector()
        self._selected_region: CaptureRegion | None = None

        # System tray
        self._tray = QSystemTrayIcon(self)
        icon_file = asset_path("captokey.png")
        if icon_file.exists():
            self._tray.setIcon(QIcon(str(icon_file)))
        else:
            self._tray.setIcon(app.windowIcon())

        # Tray context menu
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu
        self._tray_menu = QMenu()
        self._action_record = QAction("Record", self)
        self._action_pause = QAction("Pause", self)
        self._action_stop = QAction("Stop", self)
        self._action_show = QAction("Show CaptoKey", self)
        self._action_quit = QAction("Quit", self)
        self._action_record.triggered.connect(self._start_recording)
        self._action_pause.triggered.connect(self.controller.toggle_pause)
        self._action_stop.triggered.connect(self._stop_recording)
        self._action_show.triggered.connect(self._show_window)
        self._action_quit.triggered.connect(app.quit)
        self._tray_menu.addAction(self._action_record)
        self._tray_menu.addAction(self._action_pause)
        self._tray_menu.addAction(self._action_stop)
        self._tray_menu.addSeparator()
        self._tray_menu.addAction(self._action_show)
        self._tray_menu.addAction(self._action_quit)
        self._tray.setContextMenu(self._tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

        # Global hotkeys — disabled for now (macOS crash investigation)
        self._global_hotkeys = None

        self.window.startRequested.connect(self._start_recording)
        self.window.stopRequested.connect(self._stop_recording)
        self.window.pauseToggled.connect(self.controller.toggle_pause)
        self.window.settingsRequested.connect(self._open_settings)
        self.window.renderAgainRequested.connect(self.controller.rerender)
        self.controller.statsUpdated.connect(self.window.update_metrics)
        self.controller.stateChanged.connect(self._on_state_changed)
        self.controller.errorRaised.connect(self.window.show_error)
        self.controller.sessionSaved.connect(self._handle_saved_session)
        self.selector.regionSelected.connect(self._begin_recording_with_region)
        self.selector.selectionCancelled.connect(self.window.showNormal)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(250)
        self._poll_timer.timeout.connect(self.controller.poll)
        self._poll_timer.start()

        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._do_start_full_display_recording)

        self.window.show()
        self.window.set_recording_state(active=False, paused=False)

    def _start_recording(self) -> None:
        allowed, msg = _macos_ensure_screen_capture()
        if not allowed:
            self.window.show_error(msg)
            return
        self.window.set_starting_state()
        self.window.hide()
        self._app.processEvents()
        if self.settings.capture_mode == "region":
            self.selector.start()
            return
        self._delay_timer.start(400)

    def _do_start_full_display_recording(self) -> None:
        try:
            region = default_region_for_primary_screen()
        except Exception as exc:
            self.window.showNormal()
            self.window.show_error(str(exc))
            return
        self._begin_recording_with_region(region)

    def _stop_recording(self) -> None:
        self.controller.stop()
        # Restore the window immediately so the user sees the completion dialog
        self.window.showNormal()
        self.window.raise_()

    def _begin_recording_with_region(self, region: CaptureRegion) -> None:
        self._selected_region = region
        self.window.update_scope(f"{region.width}×{region.height}")
        self._app.processEvents()
        try:
            self.controller.start(region)
        except Exception as exc:
            self.window.showNormal()
            self.window.set_recording_state(False, False)
            self.window.show_error(str(exc))
            return

    def _show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _on_global_hotkey(self, name: str) -> None:
        if name == "record" and not self.controller._snapshot.active:
            self._start_recording()
        elif name == "pause" and self.controller._snapshot.active:
            self.controller.toggle_pause()
        elif name == "stop" and self.controller._snapshot.active:
            self._stop_recording()

    def _on_state_changed(self, active: bool, paused: bool) -> None:
        self.window.set_recording_state(active, paused)
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

        # Update tray menu enabled states
        self._action_record.setEnabled(not active)
        self._action_pause.setEnabled(active)
        self._action_stop.setEnabled(active)

        # Tray notification
        if active and not paused:
            self._tray.showMessage("CaptoKey", "Recording started", QSystemTrayIcon.MessageIcon.Information, 2000)
        elif active and paused:
            self._tray.showMessage("CaptoKey", "Recording paused", QSystemTrayIcon.MessageIcon.Information, 2000)
        elif not active:
            self._tray.showMessage("CaptoKey", "Recording stopped", QSystemTrayIcon.MessageIcon.Information, 2000)

    def _open_settings(self) -> None:
        updated = self.window.prompt_settings(self.settings)
        if updated is None:
            return
        self.settings = updated
        self.settings_store.save(updated)
        self.controller.settings = updated
        self.window.update_scope(updated.capture_mode.replace("_", " ").title())

    def _handle_saved_session(self, session_dir: str) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.update_metrics(0, 0, 0)
        self.window.update_scope(self.settings.capture_mode.replace("_", " ").title())
        self.window.show_completion(Path(session_dir))


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("CaptoKey")
    app.setOrganizationName("Kilo")
    icon_file = asset_path("captokey.png")
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))
    controller = ScreenRecordApplication(app)
    sys.exit(app.exec())
