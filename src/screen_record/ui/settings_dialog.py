from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
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
        self.resize(460, 320)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.save_dir_edit = QLineEdit(settings.save_dir)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_directory)

        location_row = QHBoxLayout()
        location_row.addWidget(self.save_dir_edit)
        location_row.addWidget(browse_button)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 60)
        self.fps_spin.setValue(settings.target_fps)

        self.capture_mode_combo = QComboBox()
        self.capture_mode_combo.addItem("Full display", "full_display")
        self.capture_mode_combo.addItem("Select region each time", "region")
        index = self.capture_mode_combo.findData(settings.capture_mode)
        self.capture_mode_combo.setCurrentIndex(max(0, index))

        self.ffmpeg_edit = QLineEdit(settings.ffmpeg_path)

        form = QFormLayout()
        form.addRow("Save location", self._panel(location_row))
        form.addRow("Capture mode", self.capture_mode_combo)
        form.addRow("FPS", self.fps_spin)
        form.addRow("FFmpeg path", self.ffmpeg_edit)

        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        root = QVBoxLayout(self)
        title = QLabel("Save Location")
        title.setObjectName("sectionTitle")
        root.addWidget(title)
        subtitle = QLabel("Choose where recorded videos will be saved.")
        subtitle.setObjectName("sectionSubtitle")
        root.addWidget(subtitle)
        root.addLayout(form)
        root.addStretch(1)
        root.addLayout(buttons)

        self.setStyleSheet(
            """
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0B0F16, stop:1 #111827);
                color: #F5F7FA;
                border: 1px solid #242B38;
                border-radius: 16px;
            }
            QLabel#sectionTitle { font-size: 16px; font-weight: 700; color: #D7DDF0; }
            QLabel#sectionSubtitle { color: #8B95A7; margin-bottom: 12px; }
            QLineEdit, QComboBox, QSpinBox {
                background: #151B26;
                border: 1px solid #2A3242;
                border-radius: 10px;
                padding: 10px;
                color: #F5F7FA;
                min-height: 20px;
            }
            QPushButton {
                background: #161D28;
                border: 1px solid #2A3242;
                border-radius: 10px;
                padding: 10px 14px;
                color: #F5F7FA;
            }
            QPushButton:hover { border-color: #FF5B4A; }
            """
        )

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

    @staticmethod
    def _panel(layout: QHBoxLayout) -> QWidget:
        panel = QWidget()
        panel.setLayout(layout)
        return panel
