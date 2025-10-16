"""Executable entry point for launching the GUI application."""

import importlib
import importlib.util
import multiprocessing
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for static analysis
    from PySide6.QtWidgets import QApplication
    from .gui import MainWindow


def _ensure_pyside_available() -> None:
    """Make sure PySide6 is importable before the GUI modules are loaded."""

    if importlib.util.find_spec("PySide6") is None:
        raise ModuleNotFoundError(
            "PySide6 is required to launch the GUI. Install it with 'pip install -r requirements.txt'."
        )


def _ensure_mido_installed() -> None:
    """Install mido on demand so MIDI scanning always works for new users."""

    try:
        importlib.import_module("mido")
    except ModuleNotFoundError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mido"])
        importlib.invalidate_caches()
        importlib.import_module("mido")


def main() -> None:
    """Create the Qt application, show the main window, and start the event loop."""
    _ensure_pyside_available()
    _ensure_mido_installed()

    from PySide6.QtWidgets import QApplication

    from .gui import MainWindow

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # Required for PyInstaller + Windows multiprocessing builds so child
    # processes do not spawn duplicate GUI windows; regular execution is
    # otherwise unchanged.
    multiprocessing.freeze_support()
    main()
