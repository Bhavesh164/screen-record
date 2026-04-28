from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from screen_record.models import AppSettings, CaptureRegion
from screen_record.ui.settings_dialog import SettingsDialog


class StatCard(QFrame):
    def __init__(self, title: str, value: str, icon: str) -> None:
        super().__init__()
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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        layout.addLayout(top_layout)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class RecorderWindow(QMainWindow):
    startRequested = Signal()
    stopRequested = Signal()
    pauseToggled = Signal()
    settingsRequested = Signal()
    renderAgainRequested = Signal(str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.setWindowTitle("CaptoKey")
        self.setFixedSize(280, 380)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self._latest_session_dir: Path | None = None
        self._paused = False

        root = QWidget()
        root.setObjectName("rootPanel")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(14)

        header = QHBoxLayout()
        self.status_chip = QLabel("Ready")
        self.status_chip.setObjectName("statusChip")
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setObjectName("timer")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeAppBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.close)
        header.addWidget(self.status_chip)
        header.addStretch(1)
        header.addWidget(self.timer_label)
        header.addWidget(close_btn)
        layout.addLayout(header)

        record_shell = QVBoxLayout()
        record_shell.setSpacing(7)
        self.record_button = QPushButton("")
        self.record_button.setObjectName("recordButton")
        self.record_button.clicked.connect(self._toggle_start_stop)
        self.recording_label = QLabel("Ready to record")
        self.recording_label.setObjectName("recordingLabel")
        self.scope_label = QLabel(settings.capture_mode.replace("_", " ").title())
        self.scope_label.setObjectName("scopeLabel")
        record_shell.addWidget(self.record_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        record_shell.addWidget(self.recording_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        record_shell.addWidget(self.scope_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(record_shell)

        stats = QGridLayout()
        stats.setSpacing(10)
        self.storage_card = StatCard("Storage", "0 MB", "⛁")
        self.key_card = StatCard("Keystrokes", "0", "⌨")
        stats.addWidget(self.storage_card, 0, 0)
        stats.addWidget(self.key_card, 0, 1)
        layout.addLayout(stats)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.pause_button = QPushButton("⏸\nPause")
        self.pause_button.setObjectName("pauseBtn")
        self.pause_button.clicked.connect(self._toggle_pause)
        self.stop_button = QPushButton("⏹\nStop")
        self.stop_button.setObjectName("stopBtn")
        self.stop_button.clicked.connect(self.stopRequested.emit)
        self.settings_button = QPushButton("⚙\nSettings")
        self.settings_button.setObjectName("settingsBtn")
        self.settings_button.clicked.connect(self.settingsRequested.emit)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.settings_button)
        layout.addLayout(controls)

        self.setStyleSheet(
            """
            QMainWindow {
                background: transparent;
            }
            QWidget#rootPanel {
                background: #12151C;
                color: #F8FAFC;
                border: 1px solid #1E232D;
                border-radius: 12px;
            }
            QLabel#statusChip {
                background: #1A3B29;
                color: #69E18A;
                padding: 4px 10px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#timer { color: #F8FAFC; font-size: 14px; font-weight: 600; margin-right: 8px; }
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
            QLabel {
                background: transparent;
                border: none;
                color: #F8FAFC;
            }
            QPushButton#recordButton {
                min-width: 84px;
                max-width: 84px;
                min-height: 84px;
                max-height: 84px;
                border-radius: 42px;
                background: #FF4D4D;
                border: 6px solid #1E232D;
            }
            QPushButton#recordButton:hover { 
                background: #FF6666;
            }
            QPushButton#recordButton:disabled { opacity: 0.5; }
            QLabel#recordingLabel {
                background: transparent;
                border: none;
                color: #F8FAFC;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#scopeLabel {
                background: transparent;
                border: none;
                color: #9AA4B2;
                font-size: 11px;
            }
            QFrame {
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
            QLabel#statValue { color: #F8FAFC; font-size: 14px; font-weight: 600; }
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 6px;
                color: #9AA4B2;
                font-size: 11px;
            }
            QPushButton:hover { background: #1E232D; color: #F8FAFC; }
            QPushButton#stopBtn { color: #FF4B4B; }
            QPushButton#stopBtn:hover { background: #1E232D; color: #FF6666; }
            """
        )

        self._drag_start = None
        self._poller = QTimer(self)
        self._poller.setInterval(250)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_start = None

    def set_recording_state(self, active: bool, paused: bool) -> None:
        self._paused = paused
        if active and not paused:
            self.status_chip.setText("Recording")
            self.recording_label.setText("Recording in progress")
        elif active and paused:
            self.status_chip.setText("Paused")
            self.recording_label.setText("Recording paused")
        else:
            self.status_chip.setText("Ready")
            self.recording_label.setText("Ready to record")
        self.pause_button.setText("▶\nResume" if paused else "Ⅱ\nPause")
        self.record_button.setEnabled(not active)
        self.stop_button.setEnabled(active)
        self.pause_button.setEnabled(active)

    def set_starting_state(self) -> None:
        self.status_chip.setText("Starting")
        self.recording_label.setText("Preparing capture")
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)

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
        QMessageBox.critical(self, "CaptoKey", message)

    def _toggle_start_stop(self) -> None:
        self.startRequested.emit()

    def _toggle_pause(self) -> None:
        self.pauseToggled.emit()


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
