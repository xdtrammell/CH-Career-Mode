"""Core data structures and helpers shared across the career builder."""

from dataclasses import dataclass
import re
from typing import Optional

COLOR_TAG_RE = re.compile(r'</?color\b[^>]*>', re.IGNORECASE)


OFFICIAL_CHARTERS = {
    "harmonix",
    "neversoft",
}


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


def effective_diff(song: 'Song', lower_official: bool) -> Optional[int]:
    """Return the difficulty value, optionally lowered for official charts."""
    diff = song.diff_guitar
    if diff is None:
        return None
    if lower_official and (song.charter or "").strip().lower() in OFFICIAL_CHARTERS:
        return max(1, diff - 1)
    return diff



def effective_score(song: 'Song', lower_official: bool) -> float:
    """Compute the song score with any requested charter adjustment applied."""
    adj_diff = effective_diff(song, lower_official)
    return difficulty_score(adj_diff, song.length_ms)


@dataclass
class Song:
    """Normalized metadata for a Clone Hero song used across the toolchain."""

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
