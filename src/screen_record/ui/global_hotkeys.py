from __future__ import annotations

import logging
import platform
import threading
from typing import Callable

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class GlobalHotkeyManager(QObject):
    """Global keyboard shortcuts via pynput (background thread → Qt signal).

    .. note::
        Disabled on macOS because pynput's background thread triggers
        HIToolbox assertions and crashes the app (SIGTRAP) when bundled.
    """

    triggered = Signal(str)

    def __init__(self, shortcuts: dict[str, str], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._shortcuts = shortcuts
        self._listener = None

    def start(self) -> None:
        if platform.system() == "Darwin":
            logger.info("Global hotkeys disabled on macOS")
            return
        if self._listener is not None:
            return
        try:
            from pynput import keyboard

            self._listener = keyboard.GlobalHotKeys(
                {combo: lambda name=name: self.triggered.emit(name) for name, combo in self._shortcuts.items()}
            )
            self._listener.start()
            logger.info("Global hotkeys started: %s", self._shortcuts)
        except Exception as exc:
            logger.warning("Global hotkeys unavailable: %s", exc)
            self._listener = None

    def stop(self) -> None:
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
