"""Scan Clone Hero libraries, normalise metadata, and cache song details."""

import configparser
import os
import sqlite3
from typing import Dict, List, Optional, Set

from PySide6.QtCore import QObject, Signal

from .core import Song, strip_color_tags, difficulty_score

PRIORITY = ["notes.chart", "notes.mid", "song.chart", "song.mid"]


def _project_root() -> str:
    """Return the absolute path to the repository root."""

    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def get_cache_dir(*, create: bool = True) -> str:
    """Return the directory for cached song data, creating it when requested."""

    cache_dir = os.path.join(_project_root(), ".cache")
    if create:
        os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def get_cache_path(*, create: bool = True) -> str:
    """Return the absolute path to the songs cache database."""

    return os.path.join(get_cache_dir(create=create), "songs.sqlite")


def read_song_ini(ini_path: str) -> Dict[str, str]:
    """Robust song.ini reader (no interpolation, tolerant encodings)."""
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            parser = configparser.RawConfigParser(strict=False, interpolation=None, delimiters=("="))
            parser.optionxform = str
            with open(ini_path, "r", encoding=enc, errors="ignore") as fh:
                parser.read_file(fh)
            break
        except Exception:
            parser = None
    if not parser:
        return {}

    section = "song" if parser.has_section("song") else ("Song" if parser.has_section("Song") else None)
    data: Dict[str, str] = {}
    if section:
        try:
            for k, v in parser.items(section):
                data[k] = v
        except Exception:
            try:
                with open(ini_path, "r", encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        if line.strip().startswith("["):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            data[k.strip()] = v.strip()
            except Exception:
                return {}
    return data


def find_chart_file(song_folder: str) -> Optional[str]:
    for name in PRIORITY:
        p = os.path.join(song_folder, name)
        if os.path.isfile(p):
            return p
    for root, _, files in os.walk(song_folder):
        for f in files:
            if f.lower().endswith((".chart", ".mid")):
                return os.path.join(root, f)
    return None


def has_guitar_part(chart_path: Optional[str]) -> bool:
    """Fast heuristic check for a 5-fret guitar part."""
    if not chart_path or not os.path.isfile(chart_path):
        return False
    try:
        with open(chart_path, "rb") as f:
            data = f.read()
    except Exception:
        return False
    lower = data.lower()
    if chart_path.lower().endswith(".chart"):
        for token in (b"[expertsingle]", b"[hardsingle]", b"[mediumsingle]", b"[easysingle]"):
            if token in lower:
                return True
        return False
    for token in (b"part guitar", b"part guitar coop", b"part lead", b"part rhythm"):
        if token in lower:
            return True
    return False


def md5_file(path: str) -> str:
    import hashlib

    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest().upper()



class ScanWorker(QObject):
    progress = Signal(int)
    message = Signal(str)
    done = Signal(list)

    def __init__(self, root: str, cache_db: str):
        super().__init__()
        self.root = root
        self.cache_db = cache_db
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        os.makedirs(os.path.dirname(self.cache_db), exist_ok=True)
        conn = sqlite3.connect(self.cache_db)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS songs (
                path TEXT PRIMARY KEY,
                mtime REAL,
                name TEXT,
                artist TEXT,
                charter TEXT,
                length_ms INTEGER,
                diff_guitar INTEGER,
                is_very_long INTEGER,
                chart_path TEXT,
                chart_md5 TEXT,
                score REAL,
                genre TEXT
            )
            """
        )
        conn.commit()
        try:
            cur.execute("ALTER TABLE songs ADD COLUMN genre TEXT")
        except sqlite3.OperationalError:
            pass


        total_dirs = sum(1 for _ in os.walk(self.root))
        processed_dirs = 0
        results: List[Song] = []
        seen_md5: Set[str] = set()  # Track chart hashes to avoid duplicates

        for dirpath, dirnames, filenames in os.walk(self.root):
            if self._stop:
                break
            processed_dirs += 1
            if processed_dirs % 100 == 0:
                self.progress.emit(int(processed_dirs / max(1, total_dirs) * 100))

            ini_name = None
            for candidate in ("song.ini", "Song.ini"):
                if candidate in filenames:
                    ini_name = candidate
                    break
            if not ini_name:
                continue
            ini_path = os.path.join(dirpath, ini_name)

            try:
                mtime = os.path.getmtime(ini_path)
            except Exception:
                continue

            cur.execute("SELECT mtime FROM songs WHERE path=?", (ini_path,))
            row = cur.fetchone()
            if row and abs(row[0] - mtime) < 1e-6:
                cur.execute(
                    "SELECT name,artist,charter,genre,length_ms,diff_guitar,is_very_long,chart_path,chart_md5,score FROM songs WHERE path=?",
                    (ini_path,),
                )
                row2 = cur.fetchone()
                if row2:
                    cached_genre = strip_color_tags(row2[3] or "")
                    if not cached_genre:
                        ini_data = read_song_ini(ini_path)
                        cached_genre = strip_color_tags(ini_data.get("genre")) if ini_data else ""
                        if cached_genre:
                            cur.execute("UPDATE songs SET genre=? WHERE path=?", (cached_genre, ini_path))
                            conn.commit()
                    s = Song(
                        path=ini_path,
                        name=strip_color_tags(row2[0]),
                        artist=strip_color_tags(row2[1]),
                        charter=strip_color_tags(row2[2]),
                        genre=cached_genre,
                        length_ms=row2[4],
                        diff_guitar=row2[5],
                        is_very_long=bool(row2[6]),
                        chart_path=row2[7],
                        chart_md5=row2[8],
                        score=row2[9] or 0.0,
                    )
                    chart_md5 = (s.chart_md5 or "").strip()  # Use cached MD5 to filter duplicates in-memory
                    if chart_md5 and chart_md5 in seen_md5:
                        continue
                    if s.diff_guitar is not None and s.diff_guitar >= 1:
                        results.append(s)
                        if chart_md5:
                            seen_md5.add(chart_md5)
                    continue

            data = read_song_ini(ini_path)
            if not data:
                continue

            raw_name = data.get("name")
            name = strip_color_tags(raw_name if raw_name else os.path.basename(dirpath))
            artist = strip_color_tags(data.get("artist"))
            charter = strip_color_tags(data.get("charter"))
            genre = strip_color_tags(data.get("genre"))

            try:
                length_ms = int(float(data.get("song_length", "0")))
            except Exception:
                length_ms = None

            diff_val = data.get("diff_guitar")
            try:
                diff_guitar = int(diff_val) if diff_val is not None else None
            except Exception:
                diff_guitar = None

            if diff_guitar is None or diff_guitar <= 0:
                continue

            is_very_long = bool(length_ms and length_ms >= 7 * 60 * 1000)
            chart = find_chart_file(dirpath)
            if not has_guitar_part(chart):
                continue
            chart_md5 = md5_file(chart) if chart else None
            score = difficulty_score(diff_guitar, length_ms)

            s = Song(
                path=ini_path,
                name=name,
                artist=artist,
                charter=charter,
                length_ms=length_ms,
                diff_guitar=diff_guitar,
                is_very_long=is_very_long,
                chart_path=chart,
                chart_md5=chart_md5,
                score=score,
                genre=genre,
            )
            duplicate_md5 = chart_md5.strip() if chart_md5 else ""  # Hash for deduplication within this run  # Track duplicates encountered during this run
            include_song = not duplicate_md5 or duplicate_md5 not in seen_md5
            if include_song and diff_guitar is not None and diff_guitar >= 1:
                results.append(s)
                if duplicate_md5:
                    seen_md5.add(duplicate_md5)

            cur.execute(
                "REPLACE INTO songs(path,mtime,name,artist,charter,length_ms,diff_guitar,is_very_long,chart_path,chart_md5,score,genre) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    ini_path,
                    mtime,
                    s.name,
                    s.artist,
                    s.charter,
                    s.length_ms,
                    s.diff_guitar,
                    1 if s.is_very_long else 0,
                    s.chart_path,
                    s.chart_md5,
                    s.score,
                    s.genre,
                ),
            )
            conn.commit()

        conn.close()
        self.progress.emit(100)
        self.done.emit(results)


