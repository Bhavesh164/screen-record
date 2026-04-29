from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from screen_record.models import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumSize(460, 520)
        self.setMaximumWidth(540)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._drag_start = None

        # ── Save location ──
        self.save_dir_edit = QLineEdit(settings.save_dir)
        self.save_dir_edit.setMinimumWidth(220)
        self.save_dir_edit.setPlaceholderText("Choose a directory...")
        browse_button = QPushButton("Browse")
        browse_button.setObjectName("browseBtn")
        browse_button.clicked.connect(self._browse_directory)

        loc_widget = QWidget()
        loc_layout = QHBoxLayout(loc_widget)
        loc_layout.setContentsMargins(0, 0, 0, 0)
        loc_layout.setSpacing(8)
        loc_layout.addWidget(self.save_dir_edit, 1)
        loc_layout.addWidget(browse_button)

        # ── Capture mode (custom combo) ──
        self._capture_mode_value = settings.capture_mode
        self.capture_mode_btn = QPushButton()
        self.capture_mode_btn.setObjectName("captureCombo")
        capture_menu = QMenu(self.capture_mode_btn)
        capture_menu.setObjectName("captureMenu")
        capture_menu.addAction("Full display", lambda: self._set_capture_mode("full_display", "Full display"))
        capture_menu.addAction("Select region each time", lambda: self._set_capture_mode("region", "Select region each time"))
        self.capture_mode_btn.setMenu(capture_menu)
        self._set_capture_mode(
            settings.capture_mode,
            "Full display" if settings.capture_mode == "full_display" else "Select region each time",
        )

        # ── Frame rate (custom spin) ──
        self.fps_value = settings.target_fps
        self.fps_edit = QLineEdit(str(settings.target_fps))
        self.fps_edit.setObjectName("fpsEdit")
        from PySide6.QtGui import QIntValidator
        self.fps_edit.setValidator(QIntValidator(10, 60))

        fps_up = QPushButton("▲")
        fps_up.setObjectName("fpsUpBtn")
        fps_up.setFixedSize(22, 18)
        fps_up.clicked.connect(self._fps_step_up)
        fps_down = QPushButton("▼")
        fps_down.setObjectName("fpsDownBtn")
        fps_down.setFixedSize(22, 18)
        fps_down.clicked.connect(self._fps_step_down)

        fps_btn_col = QVBoxLayout()
        fps_btn_col.setContentsMargins(0, 0, 0, 0)
        fps_btn_col.setSpacing(0)
        fps_btn_col.addWidget(fps_up)
        fps_btn_col.addWidget(fps_down)

        fps_widget = QWidget()
        fps_widget.setObjectName("fpsWidget")
        fps_layout = QHBoxLayout(fps_widget)
        fps_layout.setContentsMargins(0, 0, 0, 0)
        fps_layout.setSpacing(0)
        fps_layout.addWidget(self.fps_edit, 1)
        fps_layout.addLayout(fps_btn_col)

        # ── FFmpeg path ──
        self.ffmpeg_edit = QLineEdit(settings.ffmpeg_path)
        self.ffmpeg_edit.setPlaceholderText("Leave empty to auto-detect")

        # ── Layout ──
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setObjectName("settingsContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(24, 22, 24, 22)
        container_layout.setSpacing(16)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 4)
        title = QLabel("Settings")
        title.setObjectName("dialogTitle")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(title)
        title_layout.addStretch(1)
        title_layout.addWidget(close_btn)
        container_layout.addLayout(title_layout)

        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        container_layout.addWidget(separator)

        def make_field(title_text: str, desc_text: str, widget: QWidget) -> QVBoxLayout:
            vbox = QVBoxLayout()
            vbox.setSpacing(4)
            t = QLabel(title_text)
            t.setObjectName("fieldTitle")
            d = QLabel(desc_text)
            d.setObjectName("fieldDesc")
            d.setWordWrap(True)
            vbox.addWidget(t)
            vbox.addWidget(d)
            vbox.addWidget(widget)
            return vbox

        section = QFrame()
        section.setObjectName("settingsSection")
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(16, 14, 16, 14)
        section_layout.setSpacing(14)
        section_layout.addLayout(make_field("Save Location", "Choose where recorded videos will be saved.", loc_widget))
        section_layout.addLayout(make_field("Capture Mode", "Select how the screen is captured.", self.capture_mode_btn))
        section_layout.addLayout(make_field("Frame Rate", "Target frames per second for the recording.", fps_widget))
        section_layout.addLayout(make_field("FFmpeg Path", "Path to the FFmpeg executable.", self.ffmpeg_edit))
        container_layout.addWidget(section)

        container_layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondaryButton")
        save_button = QPushButton("Save Settings")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)
        container_layout.addLayout(buttons)

        outer_layout.addWidget(container)
        self.setStyleSheet(_SETTINGS_STYLESHEET)

    def _set_capture_mode(self, value: str, text: str) -> None:
        self._capture_mode_value = value
        self.capture_mode_btn.setText(f"{text}  ▼")

    def _fps_step_up(self) -> None:
        try:
            v = int(self.fps_edit.text())
        except ValueError:
            v = 30
        v = min(60, v + 1)
        self.fps_edit.setText(str(v))

    def _fps_step_down(self) -> None:
        try:
            v = int(self.fps_edit.text())
        except ValueError:
            v = 30
        v = max(10, v - 1)
        self.fps_edit.setText(str(v))

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_start = None

    def to_settings(self) -> AppSettings:
        try:
            fps = int(self.fps_edit.text())
        except ValueError:
            fps = 30
        fps = max(10, min(60, fps))
        return AppSettings(
            save_dir=self.save_dir_edit.text().strip() or str(Path.home() / "Downloads"),
            capture_mode=self._capture_mode_value,
            target_fps=fps,
            output_container="mp4",
            ffmpeg_path=self.ffmpeg_edit.text().strip(),
        )

    def _browse_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select save folder", self.save_dir_edit.text())
        if directory:
            self.save_dir_edit.setText(directory)


_SETTINGS_STYLESHEET = """
QDialog#settingsDialog {
    background: transparent;
}
QWidget#settingsContainer {
    background: #12151C;
    border: 1px solid #1E232D;
    border-radius: 14px;
}
QLabel {
    background: transparent;
    border: none;
    color: #F8FAFC;
}
QLabel#dialogTitle {
    font-size: 18px;
    font-weight: 700;
    color: #F8FAFC;
    padding: 0;
}
QPushButton#closeBtn {
    background: transparent;
    border: none;
    color: #6B7280;
    font-size: 16px;
    padding: 0;
}
QPushButton#closeBtn:hover {
    color: #F8FAFC;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 6px;
}
QFrame#separator {
    background: #1E232D;
    border: none;
    border-radius: 0;
}
QFrame#settingsSection {
    background: #171B24;
    border: 1px solid #242A38;
    border-radius: 10px;
}
QLabel#fieldTitle {
    color: #E2E8F0;
    font-size: 13px;
    font-weight: 600;
}
QLabel#fieldDesc {
    color: #6B7280;
    font-size: 11px;
}
QLineEdit {
    background: #0F1219;
    border: 1px solid #2A3140;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F8FAFC;
    min-height: 22px;
    selection-background-color: #A898EA;
    selection-color: #12151C;
}
QLineEdit:focus {
    border-color: #A898EA;
}
QLineEdit::placeholder {
    color: #4A5060;
}

/* ── Custom combo button ── */
QPushButton#captureCombo {
    background: #0F1219;
    border: 1px solid #2A3140;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F8FAFC;
    min-height: 22px;
    text-align: left;
    font-size: 13px;
}
QPushButton#captureCombo:focus {
    border-color: #A898EA;
}
QPushButton#captureCombo::menu-indicator {
    image: none;
    width: 0px;
}
QMenu#captureMenu {
    background: #12151C;
    border: 1px solid #2A3140;
    border-radius: 6px;
    color: #F8FAFC;
    padding: 4px;
}
QMenu#captureMenu::item {
    padding: 6px 16px;
    border-radius: 4px;
}
QMenu#captureMenu::item:selected {
    background: #A898EA;
    color: #12151C;
}

/* ── Custom FPS widget ── */
QWidget#fpsWidget {
    background: #0F1219;
    border: 1px solid #2A3140;
    border-radius: 8px;
}
QWidget#fpsWidget:focus-within {
    border-color: #A898EA;
}
QLineEdit#fpsEdit {
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 8px 12px;
    color: #F8FAFC;
    min-height: 22px;
    font-size: 13px;
}
QPushButton#fpsUpBtn, QPushButton#fpsDownBtn {
    background: #2A3140;
    border: none;
    color: #F8FAFC;
    font-size: 8px;
    padding: 0;
}
QPushButton#fpsUpBtn:hover, QPushButton#fpsDownBtn:hover {
    background: #3A4258;
}

/* ── Buttons ── */
QPushButton#browseBtn {
    background: #1E232D;
    border: 1px solid #2A3140;
    border-radius: 8px;
    padding: 8px 16px;
    color: #F8FAFC;
    font-weight: 600;
    min-width: 74px;
}
QPushButton#browseBtn:hover {
    background: #2A3140;
    border-color: #3A4258;
}
QPushButton#primaryButton {
    background: #A898EA;
    color: #12151C;
    font-weight: 700;
    font-size: 13px;
    border: none;
    border-radius: 10px;
    padding: 10px 22px;
    min-width: 120px;
}
QPushButton#primaryButton:hover {
    background: #B8A8FA;
}
QPushButton#secondaryButton {
    background: #1E232D;
    color: #C8CED8;
    font-weight: 600;
    font-size: 13px;
    border: 1px solid #2A3140;
    border-radius: 10px;
    padding: 10px 22px;
    min-width: 90px;
}
QPushButton#secondaryButton:hover {
    background: #2A3140;
    color: #F8FAFC;
    border-color: #3A4258;
}
"""
