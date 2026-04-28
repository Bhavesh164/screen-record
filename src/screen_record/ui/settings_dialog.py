from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
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
        self.setMinimumSize(480, 520)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._drag_start = None

        self.save_dir_edit = QLineEdit(settings.save_dir)
        self.save_dir_edit.setMinimumWidth(220)
        browse_button = QPushButton("Browse")
        browse_button.setObjectName("browseBtn")
        browse_button.clicked.connect(self._browse_directory)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 60)
        self.fps_spin.setValue(settings.target_fps)

        self.capture_mode_combo = QComboBox()
        self.capture_mode_combo.addItem("Full display", "full_display")
        self.capture_mode_combo.addItem("Select region each time", "region")
        index = self.capture_mode_combo.findData(settings.capture_mode)
        self.capture_mode_combo.setCurrentIndex(max(0, index))

        self.ffmpeg_edit = QLineEdit(settings.ffmpeg_path)

        section_layout = QVBoxLayout()
        section_layout.setSpacing(18)
        section_layout.setContentsMargins(18, 18, 18, 18)

        def make_field(title_text: str, desc_text: str, widget: QWidget) -> QVBoxLayout:
            vbox = QVBoxLayout()
            vbox.setSpacing(4)
            t = QLabel(title_text)
            t.setObjectName("fieldTitle")
            d = QLabel(desc_text)
            d.setObjectName("fieldDesc")
            vbox.addWidget(t)
            vbox.addWidget(d)
            vbox.addWidget(widget)
            return vbox

        # Save Location
        loc_widget = QWidget()
        loc_layout = QHBoxLayout(loc_widget)
        loc_layout.setContentsMargins(0, 0, 0, 0)
        loc_layout.setSpacing(8)
        loc_layout.addWidget(self.save_dir_edit, 1)
        loc_layout.addWidget(browse_button)
        section_layout.addLayout(make_field("Save Location", "Choose where recorded videos will be saved.", loc_widget))

        # Capture Mode
        section_layout.addLayout(make_field("Capture Mode", "Select how the screen is captured.", self.capture_mode_combo))

        # FPS
        section_layout.addLayout(make_field("Frame Rate", "Target frames per second for the recording.", self.fps_spin))

        # FFmpeg
        section_layout.addLayout(make_field("FFmpeg Path", "Path to the FFmpeg executable.", self.ffmpeg_edit))

        section = QFrame()
        section.setObjectName("settingsSection")
        section.setLayout(section_layout)

        save_button = QPushButton("Save")
        save_button.setObjectName("primaryButton")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 8)
        title = QLabel("Settings")
        title.setObjectName("dialogTitle")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(26, 26)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(title)
        title_layout.addStretch(1)
        title_layout.addWidget(close_btn)

        # Wrap everything in a container widget for rounded corners
        container = QWidget()
        container.setObjectName("settingsContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(22, 20, 22, 20)
        container_layout.setSpacing(12)
        container_layout.addLayout(title_layout)
        container_layout.addWidget(section)
        container_layout.addStretch(1)
        container_layout.addLayout(buttons)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(container)

        self.setStyleSheet(_SETTINGS_STYLESHEET)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_start = None

    def to_settings(self) -> AppSettings:
        return AppSettings(
            save_dir=self.save_dir_edit.text().strip() or str(Path.home() / "Downloads"),
            capture_mode=str(self.capture_mode_combo.currentData()),
            target_fps=int(self.fps_spin.value()),
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
    font-size: 16px;
    font-weight: 600;
}
QPushButton#closeBtn {
    background: transparent;
    border: none;
    color: #9AA4B2;
    font-size: 16px;
    padding: 0;
}
QPushButton#closeBtn:hover {
    color: #F8FAFC;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
}
QFrame#settingsSection {
    background: #171B24;
    border: 1px solid #1E232D;
    border-radius: 10px;
}
QLabel#fieldTitle {
    color: #A898EA;
    font-size: 13px;
    font-weight: 600;
}
QLabel#fieldDesc {
    color: #9AA4B2;
    font-size: 11px;
    margin-bottom: 4px;
}
QLineEdit, QComboBox, QSpinBox {
    background: #12151C;
    border: 1px solid #2A3140;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F8FAFC;
    min-height: 22px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #A898EA;
}

/* ── ComboBox dropdown arrow ── */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 30px;
    border: none;
    border-left: 1px solid #2A3140;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    background: transparent;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #9AA4B2;
    width: 0;
    height: 0;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #12151C;
    border: 1px solid #2A3140;
    border-radius: 6px;
    color: #F8FAFC;
    selection-background-color: #A898EA;
    selection-color: #12151C;
    padding: 4px;
}

/* ── SpinBox buttons ── */
QSpinBox::up-button, QSpinBox::down-button {
    background: transparent;
    border: none;
    width: 20px;
}
QSpinBox::up-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #9AA4B2;
    width: 0;
    height: 0;
}
QSpinBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #9AA4B2;
    width: 0;
    height: 0;
}

/* ── Buttons ── */
QPushButton {
    background: #1E232D;
    border: 1px solid #2A3140;
    border-radius: 8px;
    padding: 9px 18px;
    color: #F8FAFC;
}
QPushButton:hover {
    background: #2A3140;
}
QPushButton#browseBtn {
    min-width: 70px;
}
QPushButton#primaryButton {
    background: #A898EA;
    color: #12151C;
    font-weight: 600;
    border: none;
    padding: 9px 24px;
}
QPushButton#primaryButton:hover {
    background: #B8A8FA;
}
"""
