from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPainter, QPixmap
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
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)

from screen_record.models import AppSettings


def _arrow_image_paths() -> dict[str, str]:
    tmp = tempfile.gettempdir()
    paths = {
        "combo_down": os.path.join(tmp, "captokey_combo_down.png"),
        "spin_up": os.path.join(tmp, "captokey_spin_up.png"),
        "spin_down": os.path.join(tmp, "captokey_spin_down.png"),
    }

    # Combo down arrow (10x6)
    pm = QPixmap(10, 6)
    pm.fill(QColor("transparent"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#9AA4B2"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon([QPoint(0, 0), QPoint(10, 0), QPoint(5, 6)])
    p.end()
    pm.save(paths["combo_down"])

    # Spin up arrow (8x5)
    pm = QPixmap(8, 5)
    pm.fill(QColor("transparent"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#9AA4B2"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon([QPoint(4, 0), QPoint(0, 5), QPoint(8, 5)])
    p.end()
    pm.save(paths["spin_up"])

    # Spin down arrow (8x5)
    pm = QPixmap(8, 5)
    pm.fill(QColor("transparent"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#9AA4B2"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon([QPoint(0, 0), QPoint(8, 0), QPoint(4, 5)])
    p.end()
    pm.save(paths["spin_down"])

    return paths


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumSize(460, 520)
        self.setMaximumWidth(540)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._drag_start = None

        self.save_dir_edit = QLineEdit(settings.save_dir)
        self.save_dir_edit.setMinimumWidth(220)
        self.save_dir_edit.setPlaceholderText("Choose a directory...")
        browse_button = QPushButton("Browse")
        browse_button.setObjectName("browseBtn")
        browse_button.clicked.connect(self._browse_directory)

        fusion_style = QStyleFactory.create("Fusion")

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 60)
        self.fps_spin.setValue(settings.target_fps)
        if fusion_style is not None:
            self.fps_spin.setStyle(fusion_style)

        self.capture_mode_combo = QComboBox()
        self.capture_mode_combo.setObjectName("captureCombo")
        self.capture_mode_combo.addItem("Full display", "full_display")
        self.capture_mode_combo.addItem("Select region each time", "region")
        index = self.capture_mode_combo.findData(settings.capture_mode)
        self.capture_mode_combo.setCurrentIndex(max(0, index))
        if fusion_style is not None:
            self.capture_mode_combo.setStyle(fusion_style)

        self.ffmpeg_edit = QLineEdit(settings.ffmpeg_path)
        self.ffmpeg_edit.setPlaceholderText("Leave empty to auto-detect")

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

        loc_widget = QWidget()
        loc_layout = QHBoxLayout(loc_widget)
        loc_layout.setContentsMargins(0, 0, 0, 0)
        loc_layout.setSpacing(8)
        loc_layout.addWidget(self.save_dir_edit, 1)
        loc_layout.addWidget(browse_button)

        section = QFrame()
        section.setObjectName("settingsSection")
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(16, 14, 16, 14)
        section_layout.setSpacing(14)
        section_layout.addLayout(make_field("Save Location", "Choose where recorded videos will be saved.", loc_widget))
        section_layout.addLayout(make_field("Capture Mode", "Select how the screen is captured.", self.capture_mode_combo))
        section_layout.addLayout(make_field("Frame Rate", "Target frames per second for the recording.", self.fps_spin))
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
        arrows = _arrow_image_paths()
        stylesheet = _SETTINGS_STYLESHEET.format(
            combo_down=arrows["combo_down"],
            spin_up=arrows["spin_up"],
            spin_down=arrows["spin_down"],
        )
        self.setStyleSheet(stylesheet)

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
QLineEdit, QSpinBox {
    background: #0F1219;
    border: 1px solid #2A3140;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F8FAFC;
    min-height: 22px;
    selection-background-color: #A898EA;
    selection-color: #12151C;
}
QLineEdit:focus, QSpinBox:focus {
    border-color: #A898EA;
}
QLineEdit::placeholder {
    color: #4A5060;
}

/* ── ComboBox ── */
QComboBox#captureCombo {
    background: #0F1219;
    border: 1px solid #2A3140;
    border-radius: 8px;
    padding: 8px 12px;
    padding-right: 34px;
    color: #F8FAFC;
    min-height: 22px;
    selection-background-color: #A898EA;
    selection-color: #12151C;
}
QComboBox#captureCombo:focus {
    border-color: #A898EA;
}
QComboBox#captureCombo::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 32px;
    background: #1A1E27;
    border: none;
    border-left: 1px solid #2A3140;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QComboBox#captureCombo::down-arrow {
    image: url({combo_down});
    width: 10px;
    height: 6px;
}
QComboBox#captureCombo QAbstractItemView {
    background: #12151C;
    border: 1px solid #2A3140;
    border-radius: 6px;
    color: #F8FAFC;
    selection-background-color: #A898EA;
    selection-color: #12151C;
    padding: 4px;
    outline: none;
}

/* ── SpinBox ── */
QSpinBox {
    padding-right: 28px;
}
QSpinBox::up-button, QSpinBox::down-button {
    background: #1A1E27;
    border: none;
    border-left: 1px solid #2A3140;
    width: 22px;
}
QSpinBox::up-button {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    border-top-right-radius: 8px;
}
QSpinBox::down-button {
    subcontrol-origin: padding;
    subcontrol-position: bottom right;
    border-bottom-right-radius: 8px;
}
QSpinBox::up-arrow {
    image: url({spin_up});
    width: 8px;
    height: 5px;
}
QSpinBox::down-arrow {
    image: url({spin_down});
    width: 8px;
    height: 5px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #242A38;
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