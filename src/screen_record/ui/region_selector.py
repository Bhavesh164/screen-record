from __future__ import annotations

import sys

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
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
        self._origin = QPoint()
        self._current = QPoint()
        self._dragging = False
        self._background: QPixmap | None = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_background(self, pixmap: QPixmap) -> None:
        self._background = pixmap

    def start(self) -> None:
        self._dragging = False
        self._origin = QPoint()
        self._current = QPoint()
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        self.show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        if self._background and not self._background.isNull():
            painter.drawPixmap(self.rect(), self._background)
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
            # libx264 requires width and height divisible by 2
            w = selection.width()
            h = selection.height()
            if w % 2 != 0:
                w += 1
            if h % 2 != 0:
                h += 1
            self.regionSelected.emit(
                CaptureRegion(
                    left=selection.left(),
                    top=selection.top(),
                    width=w,
                    height=h,
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


class RecordingOverlay:
    BORDER_WIDTH = 4
    BORDER_COLOR = "#FF5B4A"
    _OVERLAY_TAG = "_cko_overlay_"

    def __init__(self) -> None:
        self._borders: list[QWidget] = []
        self._visible = False
        for i in range(4):
            w = QWidget()
            w.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.WindowDoesNotAcceptFocus
            )
            w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
            w.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
            w.setStyleSheet(f"background-color: {self.BORDER_COLOR};")
            w.hide()
            self._borders.append(w)

    def set_region(self, region: CaptureRegion) -> None:
        bw = self.BORDER_WIDTH
        left = region.left
        top = region.top
        width = region.width
        height = region.height
        self._borders[0].setGeometry(left - bw, top - bw, width + 2 * bw, bw)
        self._borders[1].setGeometry(left - bw, top + height, width + 2 * bw, bw)
        self._borders[2].setGeometry(left - bw, top, bw, height)
        self._borders[3].setGeometry(left + width, top, bw, height)

    def show(self) -> None:
        self._visible = True
        for i, b in enumerate(self._borders):
            b.setWindowTitle(f"{self._OVERLAY_TAG}{i}")
            b.show()
        self._set_mac_window_level()

    def hide(self) -> None:
        self._visible = False
        for b in self._borders:
            b.hide()

    def _set_mac_window_level(self) -> None:
        if sys.platform != "darwin":
            return
        try:
            import AppKit
            from Quartz import CGWindowLevelForKey, kCGOverlayWindowLevelKey

            level = int(CGWindowLevelForKey(kCGOverlayWindowLevelKey))
            ns_app = AppKit.NSApplication.sharedApplication()
            for win in ns_app.windows():
                if win.isVisible() and win.title().startswith(self._OVERLAY_TAG):
                    win.setLevel_(level)
                    win.setTitle_("")
        except Exception:
            pass
