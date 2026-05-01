from __future__ import annotations

import sys
from pathlib import Path

import math
import platform

from PySide6.QtCore import QSize, Qt, QTimer, Signal, QPropertyAnimation, QRect
from PySide6.QtCore import QUrl
from PySide6.QtGui import QBitmap, QBrush, QColor, QDesktopServices, QIcon, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def _platform_shortcuts() -> tuple[QKeySequence, QKeySequence, QKeySequence]:
    """Return (record, pause, stop) key sequences.

    On macOS ``Meta`` maps to the physical **Control** key (``⌃``),
    while ``Ctrl`` maps to **Command** (``⌘``).  We want the physical
    Control key on every platform.
    """
    if sys.platform == "darwin":
        return (
            QKeySequence("Meta+Alt+J"),   # ⌃⌥J  (Ctrl+Opt+J)
            QKeySequence("Meta+Alt+K"),   # ⌃⌥K
            QKeySequence("Meta+Alt+L"),   # ⌃⌥L
        )
    return (
        QKeySequence("Ctrl+Alt+J"),
        QKeySequence("Ctrl+Alt+K"),
        QKeySequence("Ctrl+Alt+L"),
    )

from screen_record.models import AppSettings, CaptureRegion
from screen_record.ui.settings_dialog import SettingsDialog


class RecordButton(QPushButton):
    _RECORD_SIZE = 80

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self._RECORD_SIZE, self._RECORD_SIZE)
        self._recording = False
        self._pulse_phase = False
        self._show_spinner = False
        self._spinner_angle = 0
        self._apply_circle_mask()

    def set_recording(self, active: bool) -> None:
        self._recording = active
        self._pulse_phase = False
        self.update()

    def set_spinner(self, show: bool, angle: int = 0) -> None:
        self._show_spinner = show
        self._spinner_angle = angle
        self.update()

    def toggle_pulse(self) -> None:
        self._pulse_phase = not self._pulse_phase
        self.update()

    def _apply_circle_mask(self) -> None:
        mask = QBitmap(self._RECORD_SIZE, self._RECORD_SIZE)
        mask.fill(Qt.GlobalColor.color0)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(Qt.GlobalColor.color1))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, self._RECORD_SIZE, self._RECORD_SIZE)
        painter.end()
        self.setMask(mask)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self._RECORD_SIZE // 2
        radius = center

        if self._show_spinner:
            painter.setPen(QPen(QColor("#1E232D"), 3))
            painter.setBrush(QColor("#0F172A"))
            painter.drawEllipse(4, 4, self._RECORD_SIZE - 8, self._RECORD_SIZE - 8)

            arc_pen = QPen(QColor("#69B8E1"), 4)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRect(10, 10, self._RECORD_SIZE - 20, self._RECORD_SIZE - 20)
            start_angle = self._spinner_angle * 16
            span_angle = 120 * 16
            painter.drawArc(rect, start_angle, span_angle)

            text_pen = QPen(QColor("#69B8E1"))
            painter.setPen(text_pen)
            font = painter.font()
            font.setPixelSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "...")

            painter.end()
            return

        if not self.isEnabled():
            painter.setPen(QPen(QColor("#1E232D"), 2))
            painter.setBrush(QColor("#6B2A2A"))
            painter.drawEllipse(2, 2, self._RECORD_SIZE - 4, self._RECORD_SIZE - 4)
            return

        border_color = QColor("#2A3040")
        fill_color = QColor("#FF4D4D")

        if self._recording:
            if self._pulse_phase:
                border_color = QColor("#4A9B64")
                fill_color = QColor("#CC3B3B")
            else:
                border_color = QColor("#69E18A")
                fill_color = QColor("#FF4D4D")

        if self.isDown() or self.underMouse():
            fill_color = fill_color.lighter(110)

        painter.setPen(QPen(border_color, 3))
        painter.setBrush(fill_color)
        painter.drawEllipse(4, 4, self._RECORD_SIZE - 8, self._RECORD_SIZE - 8)

        if self._recording:
            inner_pen = QPen(QColor("#69E18A"), 2)
            inner_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(inner_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(10, 10, self._RECORD_SIZE - 20, self._RECORD_SIZE - 20)

        painter.end()


def _macos_activate_app() -> None:
    if platform.system() != "Darwin":
        return
    try:
        import AppKit
        AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    except Exception:
        pass


def _make_tool_icon(text: str, size: int = 28) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("transparent"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor("#C8CED8"))
    font = painter.font()
    font.setPixelSize(size - 2)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return QIcon(pixmap)


class RecorderWindow(QMainWindow):
    startRequested = Signal()
    stopRequested = Signal()
    pauseToggled = Signal()
    settingsRequested = Signal()
    renderAgainRequested = Signal(str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.setWindowTitle("CaptoKey")
        self.setFixedSize(340, 440)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._latest_session_dir: Path | None = None
        self._paused = False
        self._recording_active = False
        self._processing = False
        self._spinner_angle = 0
        self._spinner_timer: QTimer | None = None

        root = QWidget()
        root.setObjectName("rootPanel")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(14)

        # ── Header ───────────────────────────────────────────────
        header = QHBoxLayout()
        self.status_chip = QLabel("Ready")
        self.status_chip.setObjectName("statusChip")
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setObjectName("timer")
        min_btn = QPushButton("—")
        min_btn.setObjectName("minimizeAppBtn")
        min_btn.setFixedSize(26, 26)
        min_btn.clicked.connect(self.hide)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeAppBtn")
        close_btn.setFixedSize(26, 26)
        close_btn.clicked.connect(self.close)
        header.addWidget(self.status_chip)
        header.addStretch(1)
        header.addWidget(self.timer_label)
        header.addWidget(min_btn)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # ── Record button ────────────────────────────────────────
        record_shell = QVBoxLayout()
        record_shell.setSpacing(8)
        self.record_button = RecordButton()
        self.record_button.setObjectName("recordButton")
        self.record_button.pressed.connect(self._on_record_clicked)
        self.recording_label = QLabel("Ready to record")
        self.recording_label.setObjectName("recordingLabel")
        self.scope_label = QLabel(settings.capture_mode.replace("_", " ").title())
        self.scope_label.setObjectName("scopeLabel")
        record_shell.addWidget(self.record_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        record_shell.addWidget(self.recording_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        record_shell.addWidget(self.scope_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(record_shell)

        # ── Divider ──────────────────────────────────────────────
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # ── Bottom controls ──────────────────────────────────────
        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.pause_button = QToolButton()
        self.pause_button.setObjectName("pauseBtn")
        self.pause_button.setAutoRaise(False)
        self.pause_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.pause_button.setIcon(_make_tool_icon("⏸"))
        self.pause_button.setText("Pause")
        self.pause_button.setIconSize(QSize(28, 28))
        self.pause_button.pressed.connect(self._on_pause_clicked)
        self.stop_button = QToolButton()
        self.stop_button.setObjectName("stopBtn")
        self.stop_button.setAutoRaise(False)
        self.stop_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.stop_button.setIcon(_make_tool_icon("⏹"))
        self.stop_button.setText("Stop")
        self.stop_button.setIconSize(QSize(28, 28))
        self.stop_button.pressed.connect(self._on_stop_clicked)
        self.settings_button = QToolButton()
        self.settings_button.setObjectName("settingsBtn")
        self.settings_button.setAutoRaise(False)
        self.settings_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.settings_button.setIcon(_make_tool_icon("⚙"))
        self.settings_button.setText("Settings")
        self.settings_button.setIconSize(QSize(28, 28))
        self.settings_button.clicked.connect(lambda: self.settingsRequested.emit())
        controls.addWidget(self.pause_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.settings_button)
        layout.addLayout(controls)

        # ── Shortcut hint ────────────────────────────────────────
        _seq_start, _seq_pause, _seq_stop = _platform_shortcuts()
        hint = QLabel("Ctrl+Alt+J: Record  ·  Ctrl+Alt+K: Pause  ·  Ctrl+Alt+L: Stop")
        hint.setObjectName("shortcutHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        # ── Keyboard shortcuts ───────────────────────────────────
        self._shortcut_start = QShortcut(_seq_start, self)
        self._shortcut_start.activated.connect(self._on_record_clicked)
        self._shortcut_pause = QShortcut(_seq_pause, self)
        self._shortcut_pause.activated.connect(self._on_pause_clicked)
        self._shortcut_stop = QShortcut(_seq_stop, self)
        self._shortcut_stop.activated.connect(self._on_stop_clicked)

        self.setStyleSheet(_MAIN_STYLESHEET)

        self._drag_start = None
        self._poller = QTimer(self)
        self._poller.setInterval(250)
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(800)
        self._pulse_timer.timeout.connect(self._toggle_pulse)

    # ── Drag support ─────────────────────────────────────────────
    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_start = None

    # ── State management ─────────────────────────────────────────
    def set_recording_state(self, active: bool, paused: bool) -> None:
        self._paused = paused
        self._recording_active = active
        if active and not paused:
            self.status_chip.setText("Recording")
            self.status_chip.setStyleSheet(
                "background: #1A3B29; color: #69E18A; padding: 4px 10px; "
                "border-radius: 10px; font-size: 11px; font-weight: 600;"
            )
            self.recording_label.setText("Recording in progress")
            self.record_button.set_recording(True)
            self._pulse_timer.start()
        elif active and paused:
            self.status_chip.setText("Paused")
            self.status_chip.setStyleSheet(
                "background: #3B3A1A; color: #E1D569; padding: 4px 10px; "
                "border-radius: 10px; font-size: 11px; font-weight: 600;"
            )
            self.recording_label.setText("Recording paused")
            self.record_button.set_recording(True)
            self._pulse_timer.stop()
        else:
            self._stop_processing()
            self.status_chip.setText("Ready")
            self.status_chip.setStyleSheet(
                "background: #1A3B29; color: #69E18A; padding: 4px 10px; "
                "border-radius: 10px; font-size: 11px; font-weight: 600;"
            )
            self.recording_label.setText("Ready to record")
            self.record_button.set_recording(False)
            self._pulse_timer.stop()
        self.pause_button.setIcon(_make_tool_icon("▶" if paused else "⏸"))
        self.pause_button.setText("Resume" if paused else "Pause")
        self.record_button.setEnabled(not active)
        self.stop_button.setEnabled(active)
        self.pause_button.setEnabled(active)

    def set_starting_state(self) -> None:
        self.status_chip.setText("Starting")
        self.status_chip.setStyleSheet(
            "background: #3B3A1A; color: #E1D569; padding: 4px 10px; "
            "border-radius: 10px; font-size: 11px; font-weight: 600;"
        )
        self.recording_label.setText("Preparing capture...")
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)

    def set_processing_state(self) -> None:
        self._processing = True
        self.status_chip.setText("Processing")
        self.status_chip.setStyleSheet(
            "background: #1A293B; color: #69B8E1; padding: 4px 10px; "
            "border-radius: 10px; font-size: 11px; font-weight: 600;"
        )
        self.recording_label.setText("Finalizing recording...")
        self.record_button.set_recording(False)
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self._spinner_angle = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(80)
        self._spinner_timer.timeout.connect(self._advance_spinner)
        self._spinner_timer.start()

    def _advance_spinner(self) -> None:
        if not self._processing:
            return
        self._spinner_angle = (self._spinner_angle + 30) % 360
        self.record_button.set_spinner(True, self._spinner_angle)

    def _stop_processing(self) -> None:
        self._processing = False
        self._spinner_angle = 0
        self.record_button.set_spinner(False)
        if hasattr(self, "_spinner_timer") and self._spinner_timer is not None:
            self._spinner_timer.stop()
            self._spinner_timer = None

    def _toggle_pulse(self) -> None:
        self.record_button.toggle_pulse()

    def update_metrics(self, elapsed_ms: int, file_size_bytes: int, keystrokes: int) -> None:
        self.timer_label.setText(_format_ms(elapsed_ms))

    def update_scope(self, text: str) -> None:
        self.scope_label.setText(text)

    def prompt_settings(self, settings: AppSettings) -> AppSettings | None:
        dialog = SettingsDialog(settings, self)
        if dialog.exec():
            return dialog.to_settings()
        return None

    def show_completion(self, session_dir: Path) -> None:
        self._latest_session_dir = session_dir
        self._stop_processing()
        # Drop stay-on-top and bring window to front
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        self.raise_()
        self.activateWindow()
        _macos_activate_app()
        # Force Qt to process the window state changes before showing the dialog
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        message = QMessageBox(self)
        message.setWindowTitle("Recording saved")
        message.setText(f"Saved recording session to:\n{session_dir}")
        open_folder = message.addButton("Open Folder", QMessageBox.ButtonRole.AcceptRole)
        open_timeline = message.addButton("Open Timeline", QMessageBox.ButtonRole.ActionRole)
        rerender = message.addButton("Render Again", QMessageBox.ButtonRole.ActionRole)
        message.addButton(QMessageBox.StandardButton.Close)
        message.exec()
        clicked = message.clickedButton()
        # Restore stay-on-top
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        if clicked == open_folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(session_dir)))
        elif clicked == open_timeline:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(session_dir / "timeline.json")))
        elif clicked == rerender:
            self.renderAgainRequested.emit(str(session_dir))

    def show_error(self, message: str) -> None:
        self._stop_processing()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        self.raise_()
        self.activateWindow()
        _macos_activate_app()
        QMessageBox.critical(self, "CaptoKey", message)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    # ── Private slots ────────────────────────────────────────────
    def _on_record_clicked(self) -> None:
        if not self._recording_active:
            self.startRequested.emit()

    def _on_pause_clicked(self) -> None:
        if self._recording_active:
            self.pauseToggled.emit()

    def _on_stop_clicked(self) -> None:
        if self._recording_active:
            self.stopRequested.emit()


# ── Helpers ──────────────────────────────────────────────────────
def _format_ms(value: int) -> str:
    total_seconds = max(0, value // 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# ── Stylesheet ───────────────────────────────────────────────────
_MAIN_STYLESHEET = """
QMainWindow {
    background: transparent;
}
QWidget#rootPanel {
    background: #12151C;
    color: #F8FAFC;
    border: 1px solid #1E232D;
    border-radius: 14px;
}

/* ── Header ── */
QLabel#statusChip {
    background: #1A3B29;
    color: #69E18A;
    padding: 4px 10px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#timer {
    color: #F8FAFC;
    font-size: 15px;
    font-weight: 600;
    margin-right: 8px;
}
QPushButton#closeAppBtn, QPushButton#minimizeAppBtn {
    background: transparent;
    border: none;
    color: #9AA4B2;
    font-size: 14px;
    padding: 0;
}
QPushButton#closeAppBtn:hover, QPushButton#minimizeAppBtn:hover {
    color: #F8FAFC;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
}

/* ── Labels inside root panel ── */
QWidget#rootPanel QLabel {
    background: transparent;
    border: none;
    color: #F8FAFC;
}

/* ── Record button (custom painted) ── */
QPushButton#recordButton {
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
}

/* ── Recording label ── */
QLabel#recordingLabel {
    color: #F8FAFC;
    font-size: 13px;
    font-weight: 600;
}
QLabel#scopeLabel {
    color: #9AA4B2;
    font-size: 11px;
}

/* ── Bottom control buttons ── */
QToolButton#pauseBtn, QToolButton#stopBtn, QToolButton#settingsBtn {
    background: #1A1E27;
    border: 1px solid #242A38;
    border-radius: 12px;
    min-height: 70px;
    min-width: 80px;
    padding: 6px 4px;
    font-size: 12px;
    font-weight: 600;
    color: #C8CED8;
}
QToolButton#pauseBtn:hover, QToolButton#settingsBtn:hover {
    background: #242A38;
    border-color: #3A4258;
    color: #F8FAFC;
}
QToolButton#pauseBtn:disabled, QToolButton#settingsBtn:disabled {
    background: #141821;
    color: #4A5060;
    border-color: #1E232D;
}

QToolButton#stopBtn {
    background: #2A1418;
    border-color: #4D2229;
    color: #FF6B6B;
}
QToolButton#stopBtn:hover {
    background: #3D1C22;
    border-color: #6B3038;
    color: #FF8888;
}
QToolButton#stopBtn:disabled {
    background: #141821;
    border-color: #1E232D;
    color: #4A5060;
}

/* ── Shortcut hint ── */
QLabel#shortcutHint {
    color: #5A6374;
    font-size: 10px;
    border: none;
    background: transparent;
}
"""
