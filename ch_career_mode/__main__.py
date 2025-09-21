"""Executable entry point for launching the GUI application."""

import sys

from PySide6.QtWidgets import QApplication

from .gui import MainWindow


def main() -> None:
    """Create the Qt application, show the main window, and start the event loop."""
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
