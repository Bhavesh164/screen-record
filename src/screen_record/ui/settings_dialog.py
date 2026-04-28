from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
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
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumSize(460, 480)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._drag_start = None

        self.save_dir_edit = QLineEdit(settings.save_dir)
        self.save_dir_edit.setMinimumWidth(220)
        browse_button = QPushButton("Browse")
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
        section_layout.setSpacing(16)

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
        loc_layout.addWidget(self.save_dir_edit)
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
        title_layout.setContentsMargins(0, 0, 0, 10)
        title = QLabel("Settings")
        title.setObjectName("dialogTitle")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(title)
        title_layout.addStretch(1)
        title_layout.addWidget(close_btn)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)
        root.addLayout(title_layout)
        root.addWidget(section)
        root.addStretch(1)
        root.addLayout(buttons)

        self.setStyleSheet(
            """
            QDialog {
                background: #12151C;
                border: 1px solid #1E232D;
                border-radius: 10px;
            }
            QLabel#dialogTitle {
                color: #F8FAFC;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#closeBtn {
                background: transparent;
                border: none;
                color: #9AA4B2;
                font-size: 14px;
            }
            QPushButton#closeBtn:hover {
                color: #F8FAFC;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            QFrame#settingsSection {
                background: #171B24;
                border: 1px solid #1E232D;
                border-radius: 8px;
                padding: 16px;
            }
            QLabel#fieldTitle {
                color: #A898EA;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#fieldDesc {
                color: #9AA4B2;
                font-size: 11px;
                margin-bottom: 4px;
            }
            QLineEdit, QComboBox, QSpinBox {
                background: #12151C;
                border: 1px solid #1E232D;
                border-radius: 6px;
                padding: 8px;
                color: #F8FAFC;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #A898EA;
            }
            QPushButton {
                background: #1E232D;
                border: 1px solid #2A3140;
                border-radius: 6px;
                padding: 8px 16px;
                color: #F8FAFC;
            }
            QPushButton:hover {
                background: #2A3140;
            }
            QPushButton#primaryButton {
                background: #A898EA;
                color: #12151C;
                font-weight: 600;
                border: none;
            }
            QPushButton#primaryButton:hover {
                background: #B8A8FA;
            }
            """
        )

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

