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
    def __init__(self, title: str, value: str) -> None:
        super().__init__()
        self.title_label = QLabel(title)
        self.value_label = QLabel(value)
        self.title_label.setObjectName("statTitle")
        self.value_label.setObjectName("statValue")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.addWidget(self.title_label)
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
        self.setWindowTitle("Screen Record")
        self.setFixedSize(240, 340)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self._latest_session_dir: Path | None = None
        self._paused = False

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header = QHBoxLayout()
        self.status_chip = QLabel("Ready")
        self.status_chip.setObjectName("statusChip")
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setObjectName("timer")
        header.addWidget(self.status_chip)
        header.addStretch(1)
        header.addWidget(self.timer_label)
        layout.addLayout(header)

        record_shell = QVBoxLayout()
        record_shell.setSpacing(6)
        self.record_button = QPushButton("●")
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
        self.storage_card = StatCard("Storage", "0 MB")
        self.key_card = StatCard("Keystrokes", "0")
        stats.addWidget(self.storage_card, 0, 0)
        stats.addWidget(self.key_card, 0, 1)
        layout.addLayout(stats)

        controls = QHBoxLayout()
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self._toggle_pause)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stopRequested.emit)
        self.settings_button = QPushButton("Settings")
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
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #12161E, stop:1 #0B1017);
                color: #F3F4F6;
                border-radius: 22px;
            }
            QLabel#statusChip {
                background: rgba(40, 180, 99, 0.15);
                color: #57D27C;
                padding: 6px 10px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#timer { font-size: 17px; font-weight: 700; }
            QPushButton#recordButton {
                min-width: 82px;
                max-width: 82px;
                min-height: 82px;
                max-height: 82px;
                border-radius: 41px;
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, stop:0 #FF6B5D, stop:0.6 #FF4D3D, stop:1 #B6241A);
                border: 6px solid rgba(255, 125, 109, 0.35);
                color: white;
                font-size: 38px;
                font-weight: 800;
            }
            QLabel#recordingLabel { font-size: 15px; font-weight: 700; }
            QLabel#scopeLabel { color: #9AA4B2; font-size: 12px; }
            QFrame {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 14px;
            }
            QLabel#statTitle { color: #8C96A6; font-size: 11px; }
            QLabel#statValue { color: #F5F7FA; font-size: 18px; font-weight: 700; }
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 10px;
                color: #E5E7EB;
            }
            QPushButton:hover { border-color: #FF5B4A; }
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
        self.pause_button.setText("Resume" if paused else "Pause")
        self.record_button.setEnabled(not active)
        self.stop_button.setEnabled(active)
        self.pause_button.setEnabled(active)

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
        QMessageBox.critical(self, "Screen Record", message)

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
    return f"{value / (1024 * 1024):.1f} MB"
