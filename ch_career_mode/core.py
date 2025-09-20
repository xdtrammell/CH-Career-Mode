from dataclasses import dataclass
import re
from typing import Optional

COLOR_TAG_RE = re.compile(r'</?color\b[^>]*>', re.IGNORECASE)


def strip_color_tags(text: Optional[str]) -> str:
    """Remove Clone Hero-style <color=...> tags from song metadata."""
    if not text:
        return ""
    return COLOR_TAG_RE.sub('', text).strip()


def difficulty_score(diff_guitar: Optional[int], length_ms: Optional[int]) -> float:
    base = 0.0 if diff_guitar is None else max(0, min(9, int(diff_guitar))) / 9.0 * 100.0
    if length_ms is None:
        return base
    minutes = length_ms / 60000.0
    length_boost = max(0.0, min(10.0, (minutes - 2.0) * 2.0))
    return base + length_boost


@dataclass
class Song:
    path: str
    name: str
    artist: str
    charter: str
    length_ms: Optional[int]
    diff_guitar: Optional[int]
    is_very_long: bool
    chart_path: Optional[str]
    chart_md5: Optional[str]
    score: float
    genre: str = ""

    def __post_init__(self) -> None:
        self.name = strip_color_tags(self.name)
        self.artist = strip_color_tags(self.artist)
        self.charter = strip_color_tags(self.charter)
        self.genre = strip_color_tags(self.genre)
