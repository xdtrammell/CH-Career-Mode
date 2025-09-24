"""Scan Clone Hero libraries, normalise metadata, and cache song details."""

import configparser
import os
import sqlite3
import sys
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, ThreadPoolExecutor, wait
from typing import Dict, List, Optional, Set, Tuple

from PySide6.QtCore import QObject, Signal

from .core import Song, strip_color_tags, difficulty_score

PRIORITY = ["notes.chart", "notes.mid", "song.chart", "song.mid"]


def _project_root() -> str:
    """Return the absolute path to the repository root or executable directory."""

    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return os.path.dirname(os.path.abspath(sys.executable))
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


def compute_chart_nps(chart_path: str) -> Tuple[float, float]:
    """Dispatch to the appropriate NPS parser based on file extension."""

    lower = chart_path.lower()
    if lower.endswith(".chart"):
        return compute_chart_nps_chart(chart_path)
    if lower.endswith(".mid"):
        return compute_chart_nps_mid(chart_path)
    return 0.0, 0.0


def compute_chart_nps_chart(chart_path: str) -> Tuple[float, float]:
    """Parse a .chart file and compute average and peak notes-per-second."""

    resolution = 192
    tempo_changes: List[Tuple[int, float]] = []  # (tick, seconds_per_tick)
    notes_by_section: Dict[str, Set[int]] = {}

    try:
        with open(chart_path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return 0.0, 0.0

    current_section: Optional[str] = None
    in_section = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip().lower()
            in_section = False
            continue
        if line.startswith("{"):
            in_section = True
            continue
        if line.startswith("}"):
            in_section = False
            current_section = None
            continue
        if not in_section or not current_section:
            continue

        if current_section == "song":
            if line.lower().startswith("resolution") and "=" in line:
                try:
                    _, value = line.split("=", 1)
                    resolution = max(1, int(value.strip()))
                except ValueError:
                    pass
            continue

        if current_section == "synctrack":
            if "=" not in line:
                continue
            left, right = line.split("=", 1)
            try:
                tick = int(left.strip())
            except ValueError:
                continue
            parts = right.strip().split()
            if len(parts) < 2 or parts[0].lower() != "b":
                continue
            try:
                bpm_raw = float(parts[1])
            except ValueError:
                continue
            bpm = bpm_raw / 1000.0
            if bpm <= 0:
                continue
            seconds_per_tick = (60.0 / bpm) / resolution
            tempo_changes.append((tick, seconds_per_tick))
            continue

        section_key = current_section.lower()
        if "=" not in line:
            continue
        left, right = line.split("=", 1)
        parts = right.strip().split()
        if not parts or parts[0].lower() != "n":
            continue
        try:
            tick = int(left.strip())
        except ValueError:
            continue
        notes_by_section.setdefault(section_key, set()).add(tick)

    if not notes_by_section:
        return 0.0, 0.0

    def _pick_section(sections: Dict[str, Set[int]]) -> Optional[Set[int]]:
        difficulty_order = ["expert", "hard", "medium", "easy"]
        for diff in difficulty_order:
            single_matches = [ticks for name, ticks in sections.items() if diff in name and "single" in name]
            if single_matches:
                return max(single_matches, key=lambda t: len(t))
            generic_matches = [ticks for name, ticks in sections.items() if diff in name]
            if generic_matches:
                return max(generic_matches, key=lambda t: len(t))
        return next(iter(sections.values()), None)

    note_ticks_set = _pick_section(notes_by_section)
    if not note_ticks_set:
        return 0.0, 0.0

    note_ticks = sorted(note_ticks_set)
    default_seconds_per_tick = (60.0 / 120.0) / max(1, resolution)
    return _compute_nps_from_ticks(note_ticks, tempo_changes, default_seconds_per_tick)


def _compute_nps_from_ticks(
    note_ticks: List[int],
    tempo_changes: List[Tuple[int, float]],
    default_seconds_per_tick: float,
) -> Tuple[float, float]:
    """Convert note ticks and tempo data into average and peak NPS values."""

    if not note_ticks:
        return 0.0, 0.0
    if len(note_ticks) < 2:
        return 0.0, float(len(note_ticks))

    sorted_tempos = sorted(tempo_changes, key=lambda item: item[0])
    if not sorted_tempos:
        sorted_tempos = [(0, default_seconds_per_tick)]
    elif sorted_tempos[0][0] > 0:
        sorted_tempos.insert(0, (0, sorted_tempos[0][1]))

    times: List[float] = []
    accumulated = 0.0
    prev_tick = sorted_tempos[0][0]
    seconds_per_tick = sorted_tempos[0][1]
    tempo_index = 1

    for tick in note_ticks:
        while tempo_index < len(sorted_tempos) and sorted_tempos[tempo_index][0] <= tick:
            change_tick, new_spt = sorted_tempos[tempo_index]
            accumulated += max(0, change_tick - prev_tick) * seconds_per_tick
            prev_tick = change_tick
            seconds_per_tick = new_spt
            tempo_index += 1
        times.append(accumulated + (tick - prev_tick) * seconds_per_tick)

    if not times:
        return 0.0, 0.0

    first_time = times[0]
    last_time = times[-1]
    duration = last_time - first_time
    avg_nps = 0.0 if duration <= 0 else len(times) / duration

    peak = 0
    left = 0
    for right, t in enumerate(times):
        while left <= right and t - times[left] > 1.0:
            left += 1
        window = right - left + 1
        if window > peak:
            peak = window

    return float(avg_nps), float(peak)


def compute_chart_nps_mid(chart_path: str) -> Tuple[float, float]:
    """Parse a MIDI file and compute average and peak notes-per-second."""

    try:
        import mido
    except ImportError:
        return 0.0, 0.0

    try:
        mid = mido.MidiFile(chart_path, clip=True)
    except Exception:
        return 0.0, 0.0

    ticks_per_beat = max(1, getattr(mid, "ticks_per_beat", 480) or 480)

    tempo_changes: List[Tuple[int, float]] = []
    track_stats: List[Tuple[object, str, int, int]] = []  # (track, name, note_count, end_tick)

    for track in mid.tracks:
        tick = 0
        track_name = ""
        note_count = 0
        for msg in track:
            tick += msg.time
            if msg.is_meta:
                if msg.type == "set_tempo":
                    us_per_beat = getattr(msg, "tempo", 0)
                    if us_per_beat and us_per_beat > 0:
                        seconds_per_tick = us_per_beat / 1_000_000.0 / ticks_per_beat
                        tempo_changes.append((tick, seconds_per_tick))
                elif msg.type == "track_name" and not track_name:
                    track_name = (msg.name or "").strip()
            elif msg.type == "note_on" and msg.velocity and msg.velocity > 0:
                note_count += 1
        track_stats.append((track, track_name, note_count, tick))

    preferred_keywords = ["part guitar", "t1 gems", "notes"]
    guitar_track = None

    for keyword in preferred_keywords:
        for track, name, note_count, _ in track_stats:
            if note_count <= 0 or not name:
                continue
            if keyword in name.lower():
                guitar_track = track
                break
        if guitar_track is not None:
            break

    if guitar_track is None:
        fallback: Optional[Tuple[object, str, int, int]] = None
        for stats in track_stats:
            track, _, note_count, end_tick = stats
            if note_count <= 0:
                continue
            if fallback is None or end_tick > fallback[3]:
                fallback = stats
        if fallback is None:
            return 0.0, 0.0
        guitar_track = fallback[0]

    raw_note_ticks: List[int] = []
    normalized_ticks: List[int] = []
    tick = 0
    for msg in guitar_track:
        tick += msg.time
        if msg.is_meta or msg.type != "note_on" or not msg.velocity or msg.velocity <= 0:
            continue
        raw_note_ticks.append(tick)
        try:
            note_value = msg.note
        except AttributeError:
            note_value = None
        if note_value is not None and note_value % 12 in {0, 1, 2, 3, 4}:
            normalized_ticks.append(tick)

    source_ticks = normalized_ticks if normalized_ticks else raw_note_ticks
    chord_ticks = sorted(set(source_ticks))
    if not chord_ticks:
        return 0.0, 0.0

    default_seconds_per_tick = (60.0 / 120.0) / ticks_per_beat
    return _compute_nps_from_ticks(chord_ticks, tempo_changes, default_seconds_per_tick)



def _compute_nps_job(payload: Tuple[str, str]) -> Tuple[str, float, float]:
    """Helper executed in worker pools that returns the NPS for a chart."""

    ini_path, chart_path = payload
    avg, peak = compute_chart_nps(chart_path)
    return ini_path, avg, peak


class ScanWorker(QObject):
    progress = Signal(int)
    message = Signal(str)
    done = Signal(list)
    nps_progress = Signal(int, int)
    nps_update = Signal(str, float, float)
    nps_done = Signal()
    finished = Signal()

    def __init__(self, root: str, cache_db: str):
        super().__init__()
        self.root = root
        self.cache_db = cache_db
        self._stop = False
        self._executor = None

    def stop(self) -> None:
        self._stop = True
        executor = self._executor
        if executor is not None:
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            finally:
                self._executor = None

    def run(self) -> None:
        os.makedirs(os.path.dirname(self.cache_db), exist_ok=True)
        conn = sqlite3.connect(self.cache_db)
        cur = conn.cursor()
        try:
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
                    genre TEXT,
                    nps_avg REAL,
                    nps_peak REAL
                )
                """
            )
            conn.commit()
            for column, col_type in (("genre", "TEXT"), ("nps_avg", "REAL"), ("nps_peak", "REAL")):
                try:
                    cur.execute(f"ALTER TABLE songs ADD COLUMN {column} {col_type}")
                except sqlite3.OperationalError:
                    pass

            total_dirs = sum(1 for _ in os.walk(self.root))
            processed_dirs = 0
            results: List[Song] = []
            songs_by_path: Dict[str, Song] = {}
            pending_jobs: List[Tuple[str, str]] = []
            seen_md5: Set[str] = set()

            for dirpath, _, filenames in os.walk(self.root):
                if self._stop:
                    break
                processed_dirs += 1
                if processed_dirs % 100 == 0 or processed_dirs == total_dirs:
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
                        "SELECT name,artist,charter,genre,length_ms,diff_guitar,is_very_long,chart_path,chart_md5,score,nps_avg,nps_peak FROM songs WHERE path=?",
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
                        chart_path_cached = row2[7]
                        raw_nps_avg = row2[10] if len(row2) > 10 else None
                        raw_nps_peak = row2[11] if len(row2) > 11 else None
                        needs_nps = (
                            chart_path_cached
                            and chart_path_cached.lower().endswith((".chart", ".mid"))
                            and (raw_nps_avg is None or raw_nps_peak is None)
                        )
                        if needs_nps:
                            pending_jobs.append((ini_path, chart_path_cached))
                        nps_avg = float(raw_nps_avg) if raw_nps_avg is not None else 0.0
                        nps_peak = float(raw_nps_peak) if raw_nps_peak is not None else 0.0
                        s = Song(
                            path=ini_path,
                            name=strip_color_tags(row2[0]),
                            artist=strip_color_tags(row2[1]),
                            charter=strip_color_tags(row2[2]),
                            genre=cached_genre,
                            length_ms=row2[4],
                            diff_guitar=row2[5],
                            is_very_long=bool(row2[6]),
                            chart_path=chart_path_cached,
                            chart_md5=row2[8],
                            score=row2[9] or 0.0,
                            nps_avg=nps_avg,
                            nps_peak=nps_peak,
                        )
                        chart_md5 = (s.chart_md5 or "").strip()
                        songs_by_path[ini_path] = s
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
                needs_nps = bool(chart and chart.lower().endswith((".chart", ".mid")))
                if needs_nps:
                    pending_jobs.append((ini_path, chart))

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
                    nps_avg=0.0,
                    nps_peak=0.0,
                )
                songs_by_path[ini_path] = s
                duplicate_md5 = chart_md5.strip() if chart_md5 else ""
                include_song = not duplicate_md5 or duplicate_md5 not in seen_md5
                if include_song and diff_guitar is not None and diff_guitar >= 1:
                    results.append(s)
                    if duplicate_md5:
                        seen_md5.add(duplicate_md5)

                cur.execute(
                    "REPLACE INTO songs(path,mtime,name,artist,charter,length_ms,diff_guitar,is_very_long,chart_path,chart_md5,score,genre,nps_avg,nps_peak) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                        None if needs_nps else s.nps_avg,
                        None if needs_nps else s.nps_peak,
                    ),
                )
                conn.commit()

            conn.commit()
            total_jobs = len(pending_jobs)
            self.progress.emit(100)
            self.nps_progress.emit(0, total_jobs)
            self.done.emit(results)
            completed = 0
            if not self._stop and total_jobs > 0:
                self.message.emit("Computing chart NPS in background...")
                cpu_count = os.cpu_count() or 1
                max_workers = max(1, cpu_count - 2)
                max_workers = max(1, min(max_workers, total_jobs))
                try:
                    executor = ProcessPoolExecutor(max_workers=max_workers)
                except Exception:
                    executor = ThreadPoolExecutor(max_workers=max_workers)
                self._executor = executor
                future_to_path = {
                    executor.submit(_compute_nps_job, job): job[0] for job in pending_jobs
                }
                pending_futures = set(future_to_path.keys())
                writes_since_commit = 0
                try:
                    while pending_futures:
                        if self._stop:
                            for future in pending_futures:
                                future.cancel()
                            break
                        done_set, _ = wait(pending_futures, timeout=0.2, return_when=FIRST_COMPLETED)
                        if not done_set:
                            continue
                        for future in done_set:
                            pending_futures.discard(future)
                            ini_path = future_to_path.pop(future, None)
                            if ini_path is None or future.cancelled():
                                continue
                            try:
                                path, avg, peak = future.result()
                            except Exception:
                                path = ini_path
                                avg = 0.0
                                peak = 0.0
                            song = songs_by_path.get(path)
                            if song:
                                song.nps_avg = avg
                                song.nps_peak = peak
                            cur.execute(
                                "UPDATE songs SET nps_avg=?, nps_peak=? WHERE path=?",
                                (avg, peak, path),
                            )
                            writes_since_commit += 1
                            if writes_since_commit >= 25:
                                conn.commit()
                                writes_since_commit = 0
                            completed += 1
                            self.nps_progress.emit(completed, total_jobs)
                            self.nps_update.emit(path, avg, peak)
                    if writes_since_commit:
                        conn.commit()
                finally:
                    try:
                        executor.shutdown(wait=not self._stop, cancel_futures=self._stop)
                    except Exception:
                        pass
                    self._executor = None
            elif total_jobs <= 0:
                self.nps_progress.emit(0, 0)
            elif self._stop and total_jobs > 0:
                self.nps_progress.emit(completed, total_jobs)

            self.nps_done.emit()
        finally:
            try:
                conn.close()
            finally:
                self.finished.emit()


