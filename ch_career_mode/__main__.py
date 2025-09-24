"""Executable entry point for launching the GUI application."""

import importlib
import subprocess
import sys

from PySide6.QtWidgets import QApplication

from .gui import MainWindow


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
    _ensure_mido_installed()
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
