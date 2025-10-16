from importlib import import_module
from typing import Any

from .core import Song, strip_color_tags, difficulty_score
from .exporter import export_setlist_binary, read_setlist_md5s
from .scanner import ScanWorker
from .tiering import auto_tier

__all__ = [
    "Song",
    "strip_color_tags",
    "difficulty_score",
    "ScanWorker",
    "auto_tier",
    "export_setlist_binary",
    "read_setlist_md5s",
    "MainWindow",
]


def __getattr__(name: str) -> Any:
    """Lazily expose GUI objects so optional Qt deps can be installed first."""

    if name == "MainWindow":
        return import_module(".gui", __name__).MainWindow
    raise AttributeError(f"module '{__name__}' has no attribute {name!r}")
