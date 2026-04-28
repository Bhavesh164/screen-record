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
        self.setMinimumSize(500, 390)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.save_dir_edit = QLineEdit(settings.save_dir)
        self.save_dir_edit.setMinimumWidth(220)
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
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        form.addRow("Save location", self._panel(location_row))
        form.addRow("Capture mode", self.capture_mode_combo)
        form.addRow("FPS", self.fps_spin)
        form.addRow("FFmpeg path", self.ffmpeg_edit)

        section = QFrame()
        section.setObjectName("settingsSection")
        section.setLayout(form)

        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(12)
        title = QLabel("Settings")
        title.setObjectName("sectionTitle")
        root.addWidget(title)
        subtitle = QLabel("Choose where videos are saved and how capture runs.")
        subtitle.setObjectName("sectionSubtitle")
        root.addWidget(subtitle)
        root.addWidget(section)
        root.addStretch(1)
        root.addLayout(buttons)

        self.setStyleSheet(
            """
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0B0F16, stop:1 #111827);
                color: #F5F7FA;
                border: 1px solid #242B38;
            }
            QLabel#sectionTitle { font-size: 18px; font-weight: 700; color: #F8FAFC; }
            QLabel#sectionSubtitle { color: #9AA4B2; margin-bottom: 4px; }
            QFrame#settingsSection {
                background: #141B27;
                border: 1px solid #242D3B;
                border-radius: 8px;
                padding: 16px;
            }
            QFrame#settingsSection QLabel {
                color: #DDE3EE;
                background: transparent;
                border: none;
            }
            QLineEdit, QComboBox, QSpinBox {
                background: #0E141D;
                border: 1px solid #2A3242;
                border-radius: 6px;
                padding: 9px;
                color: #F5F7FA;
                min-height: 18px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #4D8DFF; }
            QPushButton {
                background: #1A2230;
                border: 1px solid #2A3242;
                border-radius: 6px;
                padding: 9px 14px;
                color: #F5F7FA;
            }
            QPushButton:hover { border-color: #4D8DFF; background: #202A3B; }
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        panel.setLayout(layout)
        return panel
