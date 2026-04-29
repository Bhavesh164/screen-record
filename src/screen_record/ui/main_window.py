from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtCore import QUrl
from PySide6.QtGui import QBitmap, QBrush, QColor, QDesktopServices, QIcon, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from screen_record.models import AppSettings, CaptureRegion
from screen_record.ui.settings_dialog import SettingsDialog


class StatCard(QFrame):
    def __init__(self, title: str, value: str, icon: str) -> None:
        super().__init__()
        self.setObjectName("statCard")
        icon_label = QLabel(icon)
        icon_label.setObjectName("statIcon")
        self.title_label = QLabel(title)
        self.value_label = QLabel(value)
        self.title_label.setObjectName("statTitle")
        self.value_label.setObjectName("statValue")

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)
        top_layout.addWidget(icon_label)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        layout.addLayout(top_layout)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class RecordButton(QPushButton):
    _RECORD_SIZE = 80

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self._RECORD_SIZE, self._RECORD_SIZE)
        self._recording = False
        self._pulse_phase = False
        self._apply_circle_mask()

    def set_recording(self, active: bool) -> None:
        self._recording = active
        self._pulse_phase = False
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
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._latest_session_dir: Path | None = None
        self._paused = False
        self._recording_active = False

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
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeAppBtn")
        close_btn.setFixedSize(26, 26)
        close_btn.clicked.connect(self.close)
        header.addWidget(self.status_chip)
        header.addStretch(1)
        header.addWidget(self.timer_label)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # ── Record button ────────────────────────────────────────
        record_shell = QVBoxLayout()
        record_shell.setSpacing(8)
        self.record_button = RecordButton()
        self.record_button.setObjectName("recordButton")
        self.record_button.clicked.connect(self._on_record_clicked)
        self.recording_label = QLabel("Ready to record")
        self.recording_label.setObjectName("recordingLabel")
        self.scope_label = QLabel(settings.capture_mode.replace("_", " ").title())
        self.scope_label.setObjectName("scopeLabel")
        record_shell.addWidget(self.record_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        record_shell.addWidget(self.recording_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        record_shell.addWidget(self.scope_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(record_shell)

        # ── Stat cards ───────────────────────────────────────────
        stats = QGridLayout()
        stats.setSpacing(10)
        self.storage_card = StatCard("Storage", "0 MB", "⛁")
        self.key_card = StatCard("Keystrokes", "0", "⌨")
        stats.addWidget(self.storage_card, 0, 0)
        stats.addWidget(self.key_card, 0, 1)
        layout.addLayout(stats)

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
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.stop_button = QToolButton()
        self.stop_button.setObjectName("stopBtn")
        self.stop_button.setAutoRaise(False)
        self.stop_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.stop_button.setIcon(_make_tool_icon("⏹"))
        self.stop_button.setText("Stop")
        self.stop_button.setIconSize(QSize(28, 28))
        self.stop_button.clicked.connect(self._on_stop_clicked)
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
        hint = QLabel("⌘R: Record  ·  ⌘P: Pause  ·  ⌘S: Stop")
        hint.setObjectName("shortcutHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        # ── Keyboard shortcuts (Cmd+key on macOS) ────────────────
        self._shortcut_r = QShortcut(QKeySequence("Ctrl+R"), self)
        self._shortcut_r.activated.connect(self._on_record_clicked)
        self._shortcut_p = QShortcut(QKeySequence("Ctrl+P"), self)
        self._shortcut_p.activated.connect(self._on_pause_clicked)
        self._shortcut_s = QShortcut(QKeySequence("Ctrl+S"), self)
        self._shortcut_s.activated.connect(self._on_stop_clicked)

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

    def _toggle_pulse(self) -> None:
        self.record_button.toggle_pulse()

    def update_metrics(self, elapsed_ms: int, file_size_bytes: int, keystrokes: int) -> None:
        self.timer_label.setText(_format_ms(elapsed_ms))
        self.storage_card.set_value(_format_megabytes(file_size_bytes))
        self.key_card.set_value(f"{keystrokes:,}")

    def update_scope(self, text: str) -> None:
        self.scope_label.setText(text)

    def prompt_settings(self, settings: AppSettings) -> AppSettings | None:
        dialog = SettingsDialog(settings, self)
        if dialog.exec():
            return dialog.to_settings()
        return None

    def show_completion(self, session_dir: Path) -> None:
        self._latest_session_dir = session_dir
        self.showNormal()
        self.raise_()
        message = QMessageBox(self)
        message.setWindowTitle("Recording saved")
        message.setText(f"Saved recording session to:\n{session_dir}")
        open_folder = message.addButton("Open Folder", QMessageBox.ButtonRole.AcceptRole)
        open_timeline = message.addButton("Open Timeline", QMessageBox.ButtonRole.ActionRole)
        rerender = message.addButton("Render Again", QMessageBox.ButtonRole.ActionRole)
        message.addButton(QMessageBox.StandardButton.Close)
        message.exec()
        clicked = message.clickedButton()
        if clicked == open_folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(session_dir)))
        elif clicked == open_timeline:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(session_dir / "timeline.json")))
        elif clicked == rerender:
            self.renderAgainRequested.emit(str(session_dir))

    def show_error(self, message: str) -> None:
        self.showNormal()
        self.raise_()
        QMessageBox.critical(self, "CaptoKey", message)

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


def _format_megabytes(value: int) -> str:
    megabytes = value / (1024 * 1024)
    if megabytes >= 10 or megabytes.is_integer():
        return f"{megabytes:.0f} MB"
    return f"{megabytes:.1f} MB"


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
QPushButton#closeAppBtn {
    background: transparent;
    border: none;
    color: #9AA4B2;
    font-size: 14px;
    padding: 0;
}
QPushButton#closeAppBtn:hover {
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

/* ── Stat cards ── */
QFrame#statCard {
    background: #171B24;
    border: 1px solid #1E232D;
    border-radius: 8px;
}
QFrame#divider {
    background: #1E232D;
    border: none;
    border-radius: 0;
}
QLabel#statIcon { color: #9AA4B2; font-size: 14px; }
QLabel#statTitle { color: #9AA4B2; font-size: 11px; }
QLabel#statValue { color: #F8FAFC; font-size: 15px; font-weight: 700; }

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
