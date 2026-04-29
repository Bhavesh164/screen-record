from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, Any
from dataclasses import dataclass, field

import mss
from PySide6.QtGui import QGuiApplication

from screen_record.models import CaptureRegion


@dataclass(slots=True)
class FramePayload:
    width: int
    height: int
    bytes_bgra: bytes


class ScreenCaptureProvider(Protocol):
    def grab(self) -> FramePayload: ...


@dataclass(slots=True)
class MSSScreenCaptureProvider:
    region: CaptureRegion
    _sct: Any = field(init=False)

    def __post_init__(self) -> None:
        self._sct = mss.mss()

    def grab(self) -> FramePayload:
        shot = self._sct.grab(
            {
                "left": self.region.left,
                "top": self.region.top,
                "width": self.region.width,
                "height": self.region.height,
            }
        )
        return FramePayload(width=shot.width, height=shot.height, bytes_bgra=shot.bgra)


@dataclass(slots=True)
class WaylandQtCaptureProvider:
    region: CaptureRegion

    def grab(self) -> FramePayload:
        app = QGuiApplication.instance()
        if app is None:
            raise RuntimeError("Qt application must be running for Wayland capture")
        screen = app.primaryScreen()
        if screen is None:
            raise RuntimeError("No primary screen available")
        pixmap = screen.grabWindow(
            0,
            self.region.left,
            self.region.top,
            self.region.width,
            self.region.height,
        )
        image = pixmap.toImage().convertToFormat(pixmap.toImage().Format.Format_ARGB32)
        ptr = image.bits()
        ptr.setsize(image.sizeInBytes())
        return FramePayload(
            width=image.width(),
            height=image.height(),
            bytes_bgra=bytes(ptr[: image.sizeInBytes()]),
        )


def is_wayland_session() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def default_region_for_primary_screen() -> CaptureRegion:
    app = QGuiApplication.instance()
    if app is None:
        raise RuntimeError("Qt application must be running")
    screen = app.primaryScreen()
    if screen is None:
        raise RuntimeError("No primary screen available")
    geometry = screen.geometry()
    return CaptureRegion(
        left=geometry.left(),
        top=geometry.top(),
        width=geometry.width(),
        height=geometry.height(),
    )


def make_capture_provider(region: CaptureRegion) -> ScreenCaptureProvider:
    if is_wayland_session():
        return WaylandQtCaptureProvider(region)
    return MSSScreenCaptureProvider(region)