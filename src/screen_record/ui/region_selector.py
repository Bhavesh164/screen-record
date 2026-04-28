from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

from screen_record.models import CaptureRegion


def clamp_region(region: CaptureRegion, bounds: CaptureRegion) -> CaptureRegion:
    left = max(bounds.left, min(region.left, bounds.left + bounds.width - 1))
    top = max(bounds.top, min(region.top, bounds.top + bounds.height - 1))
    right = max(left + 1, min(region.left + region.width, bounds.left + bounds.width))
    bottom = max(top + 1, min(region.top + region.height, bounds.top + bounds.height))
    return CaptureRegion(left=left, top=top, width=right - left, height=bottom - top)


class RegionSelector(QWidget):
    regionSelected = Signal(object)
    selectionCancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self._origin = QPoint()
        self._current = QPoint()
        self._dragging = False

    def start(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(5, 8, 13, 120))

        if self._dragging:
            selection = QRect(self._origin, self._current).normalized()
            painter.fillRect(selection, QColor(255, 255, 255, 30))
            painter.setPen(QPen(QColor("#FF5B4A"), 2))
            painter.drawRect(selection)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.globalPosition().toPoint()
            self._current = self._origin
            self._dragging = True
            self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._dragging:
            self._current = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._current = event.globalPosition().toPoint()
            self._dragging = False
            selection = QRect(self._origin, self._current).normalized()
            self.hide()
            if selection.width() < 8 or selection.height() < 8:
                self.selectionCancelled.emit()
                return
            self.regionSelected.emit(
                CaptureRegion(
                    left=selection.left(),
                    top=selection.top(),
                    width=selection.width(),
                    height=selection.height(),
                )
            )

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.selectionCancelled.emit()


def primary_screen_region() -> CaptureRegion:
    screen = QApplication.primaryScreen()
    if screen is None:
        raise RuntimeError("No screen available")
    geometry = screen.geometry()
    return CaptureRegion(geometry.x(), geometry.y(), geometry.width(), geometry.height())
