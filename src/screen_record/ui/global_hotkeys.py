from __future__ import annotations

import logging
import platform
import threading

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class GlobalHotkeyManager(QObject):
    """Global keyboard shortcuts via pynput (daemon thread + Qt signals).

    .. note::
        Disabled on macOS because pynput's background thread triggers
        HIToolbox assertions and crashes the app (SIGTRAP).
    """

    triggered = Signal(str)

    def __init__(self, shortcuts: dict[str, str], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._shortcuts = shortcuts
        self._thread: threading.Thread | None = None
        self._hotkeys = None

    def start(self) -> None:
        if self._thread is not None:
            return
        if platform.system() == "Darwin":
            logger.info("Global hotkeys disabled on macOS")
            return
        try:
            from pynput.keyboard import GlobalHotKeys

            self._hotkeys = GlobalHotKeys(
                {combo: lambda name=name: self.triggered.emit(name) for name, combo in self._shortcuts.items()}
            )
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            logger.info("Global hotkeys started: %s", self._shortcuts)
        except Exception as exc:
            logger.warning("Global hotkeys unavailable: %s", exc)

    def stop(self) -> None:
        if self._hotkeys:
            try:
                self._hotkeys.stop()
            except Exception:
                pass
            self._hotkeys = None
        self._thread = None

    def _run(self) -> None:
        try:
            self._hotkeys.join()
        except Exception:
            pass
