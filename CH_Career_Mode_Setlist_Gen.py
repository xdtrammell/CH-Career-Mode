import sys
import os
import hashlib
import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Dict
import random, time
import configparser
import struct
import math

from PySide6.QtCore import Qt, QSize, QObject, Signal, QThread, QSettings
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QFileDialog, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QCheckBox, QLineEdit,
    QGroupBox, QFormLayout, QMessageBox, QScrollArea, QComboBox, QProgressDialog, QStyledItemDelegate, QAbstractItemView, QGridLayout, QSizePolicy
)

# -----------------------------
# Data models
# -----------------------------
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


# -----------------------------
# Utilities
# -----------------------------

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
            # naive fallback
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


PRIORITY = ["notes.chart", "notes.mid", "song.chart", "song.mid"]


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
    """Fast heuristic check for a 5-fret guitar part.
    .chart: search section headers for Single difficulties.
    .mid: search ASCII tokens like 'PART GUITAR'.
    """
    if not chart_path or not os.path.isfile(chart_path):
        return False
    try:
        with open(chart_path, 'rb') as f:
            data = f.read()
    except Exception:
        return False
    lower = data.lower()
    if chart_path.lower().endswith('.chart'):
        for token in (b'[expertsingle]', b'[hardsingle]', b'[mediumsingle]', b'[easysingle]'):
            if token in lower:
                return True
        return False
    else:
        for token in (b'part guitar', b'part guitar coop', b'part lead', b'part rhythm'):
            if token in lower:
                return True
        return False


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def difficulty_score(diff_guitar: Optional[int], length_ms: Optional[int]) -> float:
    base = 0.0 if diff_guitar is None else max(0, min(9, int(diff_guitar))) / 9.0 * 100.0
    if length_ms is None:
        return base
    minutes = length_ms / 60000.0
    length_boost = max(0.0, min(10.0, (minutes - 2.0) * 2.0))
    return base + length_boost


# -----------------------------
# Scanner (threaded)
# -----------------------------
class ScanWorker(QObject):
    progress = Signal(int)
    message = Signal(str)
    done = Signal(list)

    def __init__(self, root: str, cache_db: str):
        super().__init__()
        self.root = root
        self.cache_db = cache_db
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
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
                score REAL
            )
            """
        )
        conn.commit()

        # First pass: count folders
        total_dirs = 0
        for _dirpath, _dirnames, _filenames in os.walk(self.root):
            total_dirs += 1
        processed_dirs = 0

        results: List[Song] = []

        for dirpath, dirnames, filenames in os.walk(self.root):
            if self._stop:
                break
            processed_dirs += 1
            if processed_dirs % 100 == 0:
                self.progress.emit(int(processed_dirs / max(1, total_dirs) * 100))

            ini_path = None
            for f in filenames:
                if f.lower() == "song.ini":
                    ini_path = os.path.join(dirpath, f)
                    break
            if not ini_path:
                continue

            try:
                mtime = os.path.getmtime(ini_path)
            except Exception:
                continue

            # Cache quick-path
            cur.execute("SELECT mtime FROM songs WHERE path=?", (ini_path,))
            row = cur.fetchone()
            if row and abs(row[0] - mtime) < 1e-6:
                cur.execute(
                    "SELECT name,artist,charter,length_ms,diff_guitar,is_very_long,chart_path,chart_md5,score FROM songs WHERE path=?",
                    (ini_path,),
                )
                row2 = cur.fetchone()
                if row2:
                    s = Song(
                        path=ini_path,
                        name=row2[0] or "",
                        artist=row2[1] or "",
                        charter=row2[2] or "",
                        length_ms=row2[3],
                        diff_guitar=row2[4],
                        is_very_long=bool(row2[5]),
                        chart_path=row2[6],
                        chart_md5=row2[7],
                        score=row2[8] or 0.0,
                    )
                    # Hard rule: exclude zero-difficulty
                    if s.diff_guitar is not None and s.diff_guitar >= 1:
                        results.append(s)
                    continue

            data = read_song_ini(ini_path)
            if not data:
                continue

            name = data.get("name", os.path.basename(dirpath))
            artist = data.get("artist", "")
            charter = data.get("charter", "")

            try:
                length_ms = int(float(data.get("song_length", "0")))
            except Exception:
                length_ms = None

            diff_val = data.get("diff_guitar")
            try:
                diff_guitar = int(diff_val) if diff_val is not None else None
            except Exception:
                diff_guitar = None

            # Hard rule: skip missing/invalid OR zero-difficulty
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
            )
            results.append(s)

            # upsert cache
            cur.execute(
                "REPLACE INTO songs(path,mtime,name,artist,charter,length_ms,diff_guitar,is_very_long,chart_path,chart_md5,score) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
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
                ),
            )
            conn.commit()

        conn.close()
        self.progress.emit(100)
        self.done.emit(results)


# -----------------------------
# Tiering logic
# -----------------------------

def auto_tier(songs: List[Song], n_tiers: int, songs_per_tier: int,
              enforce_artist_limit: bool = True,
              keep_very_long_out_of_first_two: bool = True,
              shuffle_seed: Optional[int] = None) -> List[List[Song]]:
    """Stratified tiering with randomness within difficulty quantiles.
    - Split songs into n_tiers quantile buckets by score.
    - For each tier, randomly sample from its bucket (respecting constraints).
    - If a bucket can't fill a tier, widen into neighboring songs.
    This keeps later tiers harder *and* varies picks each run, including tier 6.
    """
    rnd = random.Random(shuffle_seed if shuffle_seed is not None else time.time_ns())
    songs_sorted = sorted(songs, key=lambda s: s.score)
    N = len(songs_sorted)
    if N == 0:
        return [[] for _ in range(n_tiers)]

    # Helper: attempt to select K songs from a candidate pool with constraints
    def select_with_constraints(ti: int, pool: List[Song], k: int) -> List[Song]:
        picks: List[Song] = []
        artist_counts: Dict[str, int] = {}
        rnd.shuffle(pool)
        for s in pool:
            if len(picks) >= k:
                break
            if keep_very_long_out_of_first_two and ti < 2 and s.is_very_long:
                continue
            if enforce_artist_limit and s.artist and artist_counts.get(s.artist, 0) >= 1:
                continue
            picks.append(s)
            if s.artist:
                artist_counts[s.artist] = artist_counts.get(s.artist, 0) + 1
        return picks

    tiers: List[List[Song]] = [[] for _ in range(n_tiers)]

    # Build buckets by quantile index ranges
    for ti in range(n_tiers):
        lo = int(ti * N / n_tiers)
        hi = int((ti + 1) * N / n_tiers)
        bucket = songs_sorted[lo:hi]

        picks = select_with_constraints(ti, bucket.copy(), songs_per_tier)

        # If not enough, gradually widen: take neighbors from near the bucket edges
        expand = 1
        while len(picks) < songs_per_tier and (lo - expand >= 0 or hi + expand <= N):
            extra: List[Song] = []
            left_lo = max(0, lo - expand)
            right_hi = min(N, hi + expand)
            extra = songs_sorted[left_lo:lo] + songs_sorted[hi:right_hi]
            # avoid already chosen
            extra = [s for s in extra if s not in picks]
            # try to fill remaining slots
            need = songs_per_tier - len(picks)
            more = select_with_constraints(ti, extra, need)
            for s in more:
                if s not in picks:
                    picks.append(s)
            expand += 1
        tiers[ti] = picks[:songs_per_tier]

    return tiers


# -----------------------------
# Exporter - native Clone Hero .setlist (binary)
# -----------------------------
MAGIC = b"\xEA\xEC\x33\x01"

def export_setlist_binary(order: List[Song], out_path: str) -> None:
    md5s: List[str] = []
    for s in order:
        if not s.chart_md5:
            raise RuntimeError(f"Missing chart MD5 for: {s.name}")
        md5s.append(s.chart_md5)

    with open(out_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<I", len(md5s)))
        for h in md5s:
            f.write(b"\x20")
            f.write(h.encode("ascii"))
            f.write(b"\x64\x00")


def read_setlist_md5s(path: str) -> List[str]:
    md5s: List[str] = []
    with open(path, "rb") as f:
        header = f.read(4)
        if header != MAGIC:
            raise RuntimeError("Invalid setlist header")
        (count,) = struct.unpack("<I", f.read(4))
        for _ in range(count):
            if f.read(1) != b"\x20":
                raise RuntimeError("Malformed entry")
            h = f.read(32).decode("ascii")
            if f.read(2) != b"\x64\x00":
                raise RuntimeError("Malformed tail")
            md5s.append(h)
    return md5s


# -----------------------------
# GUI
# -----------------------------
GH_TIER_NAMES = [
    "Opening Act",
    "Local Gig",
    "Small Club",
    "Battle of the Bands",
    "Tour Bus",
    "Arena Show",
    "Stadium Rock",
    "Legends Set",
    "Encore Nights",
    "World Tour",
    "Finale",
    "Hall of Fame",
]

TIER_COLUMNS = 3




def tier_name_for(i: int, theme: str) -> str:
    if "Guitar Hero" in theme:
        return GH_TIER_NAMES[i] if i < len(GH_TIER_NAMES) else f"Tier {i+1}"
    return f"Tier {i+1}"



COMPACT_LIST_STYLE = """
QListWidget {
    border: 1px solid #2c2c2c;
    padding: 2px;
}
QListWidget::item {
    padding: 2px 6px;
}
QListWidget::item:selected {
    background-color: #3c3c3c;
}
"""


class CompactItemDelegate(QStyledItemDelegate):
    """Shrinks list row height so more songs fit on screen."""

    def __init__(self, vertical_padding: int = 2, parent=None):
        super().__init__(parent)
        self.vertical_padding = max(0, vertical_padding)

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        fm_height = option.fontMetrics.height()
        size.setHeight(fm_height + self.vertical_padding * 2)
        return size


class TierList(QListWidget):
    def __init__(self, title: str):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setMinimumWidth(200)
        self.title = title

    def sizeHint(self):
        return QSize(220, 360)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clone Hero Career Builder")
        self.resize(1280, 760)

        self.settings = QSettings("CHCareer", "Builder")

        self.library: List[Song] = []
        self.tiers_widgets: List[TierList] = []
        self.tier_wrappers: List[QWidget] = []
        self._list_delegates: List[CompactItemDelegate] = []

        # Controls
        self.btn_pick = QPushButton("Pick Songs Folder...")
        self.btn_scan = QPushButton("Scan (recursive)")
        self.btn_auto = QPushButton("Auto-Arrange")
        self.btn_export = QPushButton("Export Setlist...")

        self.search_box = QLineEdit(); self.search_box.setPlaceholderText("Search title / artist / charter...")
        self.diff_min = QSpinBox(); self.diff_min.setRange(0, 9); self.diff_min.setValue(0)
        self.diff_max = QSpinBox(); self.diff_max.setRange(0, 9); self.diff_max.setValue(9)
        self.chk_longrule = QCheckBox("Keep >7:00 out of first two tiers"); self.chk_longrule.setChecked(True)
        self.chk_artistlimit = QCheckBox("Max 1 per artist per tier"); self.chk_artistlimit.setChecked(True)

        self.spin_tiers = QSpinBox(); self.spin_tiers.setRange(1, 20); self.spin_tiers.setValue(6)
        self.spin_songs_per = QSpinBox(); self.spin_songs_per.setRange(1, 10); self.spin_songs_per.setValue(5)
        self.spin_songs_per.valueChanged.connect(lambda _=None: self._sync_all_tier_heights())

        self.theme_combo = QComboBox(); self.theme_combo.addItems(["Guitar Hero - Classic Venue Names", "None (Custom Tier Names)"])

        # Left: Library list
        self.lib_list = QListWidget(); self.lib_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.lib_list.setDragEnabled(True); self.lib_list.setDefaultDropAction(Qt.MoveAction)
        self._list_delegates.append(self._apply_compact_list_style(self.lib_list))

        # Center: Tiers area
        self.tiers_container = QWidget()
        self.tiers_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.tiers_layout = QGridLayout(self.tiers_container)
        self.tiers_layout.setContentsMargins(0, 0, 0, 0)
        self.tiers_layout.setHorizontalSpacing(8)
        self.tiers_layout.setVerticalSpacing(8)
        self.tiers_layout.setAlignment(Qt.AlignTop)

        self.tiers_scroll = QScrollArea()
        self.tiers_scroll.setWidgetResizable(True)
        self.tiers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tiers_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tiers_scroll.setWidget(self.tiers_container)

        self._rebuild_tier_widgets()

        # Right: Settings
        settings_box = QGroupBox("Settings")
        form = QFormLayout(settings_box)

        form.setSpacing(6)
        form.setContentsMargins(8, 8, 8, 8)
        form.addRow(self.btn_pick, self.btn_scan)
        form.addRow(QLabel("Tiers:"), self.spin_tiers)
        form.addRow(QLabel("Songs per tier:"), self.spin_songs_per)
        form.addRow(self.chk_artistlimit)
        form.addRow(self.chk_longrule)
        form.addRow(QLabel("Theme:"), self.theme_combo)
        form.addRow(QLabel("Search:"), self.search_box)
        form.addRow(self.btn_auto, self.btn_export)

        # Layout
        central = QWidget(); self.setCentralWidget(central)
        h = QHBoxLayout(central)
        h.setContentsMargins(8, 8, 8, 8)
        h.setSpacing(12)

        left_box = QVBoxLayout()
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(4)
        left_box.addWidget(QLabel("Library"))
        left_box.addWidget(self.lib_list, 1)
        tip_label = QLabel("Tip: drag songs into tiers; double-click to remove from a tier")
        tip_label.setWordWrap(True)
        tip_label.setContentsMargins(0, 4, 0, 0)
        left_box.addWidget(tip_label)

        h.addLayout(left_box, 2)
        h.addWidget(self.tiers_scroll, 3)
        h.addWidget(settings_box, 1)

        # Events
        self.btn_pick.clicked.connect(self.pick_folder)
        self.btn_scan.clicked.connect(self.scan_now)
        self.btn_auto.clicked.connect(self.auto_arrange)
        self.btn_export.clicked.connect(self.export_now)
        self.spin_tiers.valueChanged.connect(self._rebuild_tier_widgets)
        self.search_box.textChanged.connect(self._refresh_library_view)

        # Restore last root
        self.root_folder: Optional[str] = self.settings.value("root_folder", None, type=str)

    # ---------- UI helpers ----------
    def _apply_compact_list_style(self, widget: QListWidget) -> CompactItemDelegate:
        widget.setStyleSheet(COMPACT_LIST_STYLE)
        widget.setSpacing(1)
        widget.setUniformItemSizes(True)
        widget.setWordWrap(False)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        delegate = CompactItemDelegate(1, widget)
        widget.setItemDelegate(delegate)
        return delegate


    def _rebuild_tier_widgets(self):
        self._list_delegates = self._list_delegates[:1]
        self.tiers_widgets.clear()
        self.tier_wrappers.clear()

        while self.tiers_layout.count():
            item = self.tiers_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        cols = TIER_COLUMNS
        tier_count = self.spin_tiers.value()
        for idx in range(tier_count):
            tier = TierList(f"Tier {idx + 1}")
            tier.itemDoubleClicked.connect(lambda item, t=tier: self._remove_from_tier(t, item))
            self._list_delegates.append(self._apply_compact_list_style(tier))

            wrapper = self._create_tier_panel(tier)
            row = idx // cols
            col = idx % cols
            self.tiers_layout.addWidget(wrapper, row, col)
            self.tiers_widgets.append(tier)
            self.tier_wrappers.append(wrapper)

            model = tier.model()
            model.rowsInserted.connect(lambda *_, t=tier: self._sync_tier_height(t))
            model.rowsRemoved.connect(lambda *_, t=tier: self._sync_tier_height(t))
            self._sync_tier_height(tier)

        for col in range(cols):
            self.tiers_layout.setColumnStretch(col, 1)

        remainder = tier_count % cols
        if remainder:
            row = tier_count // cols
            for col in range(remainder, cols):
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                self.tiers_layout.addWidget(spacer, row, col)

        self._sync_all_tier_heights()

    def _create_tier_panel(self, tier: TierList) -> QWidget:
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        title = QLabel(tier.title)
        title.setAlignment(Qt.AlignHCenter)
        title.setStyleSheet('font-weight: bold;')
        layout.addWidget(title)

        tier.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tier.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(tier)
        return panel

    def _sync_tier_height(self, tier: TierList) -> None:
        target_rows = max(self.spin_songs_per.value(), tier.count())
        height = self._tier_height_for(tier, target_rows)
        tier.setFixedHeight(height)
        parent = tier.parentWidget()
        if parent:
            parent.updateGeometry()

    def _tier_height_for(self, tier: QListWidget, rows: int) -> int:
        if rows <= 0:
            rows = 1
        if tier.count():
            row_height = tier.sizeHintForRow(0)
        elif self.lib_list.count():
            row_height = self.lib_list.sizeHintForRow(0)
        else:
            row_height = tier.fontMetrics().height() + 4
        spacing = tier.spacing()
        frame = tier.frameWidth() * 2
        total_rows = rows
        return total_rows * row_height + max(0, total_rows - 1) * spacing + frame + 2

    def _sync_all_tier_heights(self) -> None:
        for tier in self.tiers_widgets:
            self._sync_tier_height(tier)

        if not self.tier_wrappers:
            self.tiers_container.setMinimumHeight(0)
            return

        rows = math.ceil(len(self.tier_wrappers) / max(1, TIER_COLUMNS))
        panel_heights = [wrapper.sizeHint().height() for wrapper in self.tier_wrappers]
        if not panel_heights:
            self.tiers_container.setMinimumHeight(0)
            return
        panel_height = max(panel_heights)
        margins = self.tiers_layout.contentsMargins()
        spacing = self.tiers_layout.verticalSpacing()
        total_height = rows * panel_height + max(0, rows - 1) * spacing + margins.top() + margins.bottom()
        self.tiers_container.setMinimumHeight(total_height)

    def _remove_from_tier(self, tier_widget: TierList, item: QListWidgetItem):
        tier_widget.takeItem(tier_widget.row(item))
        self._sync_tier_height(tier_widget)
        self._sync_all_tier_heights()


    def _build_song_item(self, song: Song) -> QListWidgetItem:
        has_length = song.length_ms is not None and song.length_ms >= 0
        if has_length:
            mins = song.length_ms // 60000
            secs = (song.length_ms // 1000) % 60
            length_str = f"{mins}:{secs:02d}"
        else:
            length_str = None

        artist_segment = f" - {song.artist}" if song.artist else ""
        length_segment = f" [{length_str}]" if length_str else ""
        item = QListWidgetItem(f"{song.name}{artist_segment}{length_segment}")

        details = []
        if song.artist:
            details.append(f"Artist: {song.artist}")
        if song.charter:
            details.append(f"Charter: {song.charter}")
        difficulty_text = f"D{song.diff_guitar}" if song.diff_guitar is not None else "Unknown"
        details.append(f"Difficulty: {difficulty_text}")
        details.append(f"Score: {int(song.score)}")
        if length_str:
            details.append(f"Length: {length_str}")
        item.setToolTip("\n".join(details))
        item.setData(Qt.UserRole, song)
        return item

    def _refresh_library_view(self):
        q = self.search_box.text().lower().strip()
        self.lib_list.clear()
        for s in sorted(self.library, key=lambda s: (s.score, s.name.lower())):
            if q:
                if q not in s.name.lower() and q not in (s.artist or "").lower() and q not in (s.charter or "").lower():
                    continue
            d = s.diff_guitar if s.diff_guitar is not None else -1
            if not (self.diff_min.value() <= d <= self.diff_max.value()):
                continue
            item = self._build_song_item(s)
            self.lib_list.addItem(item)
        self._sync_all_tier_heights()

    # ---------- Actions ----------
    def pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Pick top-level Clone Hero songs root")
        if d:
            self.root_folder = d
            self.settings.setValue("root_folder", d)

    def scan_now(self):
        if not self.root_folder:
            QMessageBox.warning(self, "No folder", "Please pick your TOP-LEVEL songs folder first.")
            return

        self.progress = QProgressDialog("Scanning songs...", "Cancel", 0, 100, self)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setAutoClose(True)
        self.progress.setMinimumDuration(0)

        self.thread = QThread(self)
        cache_db = os.path.join(os.path.expanduser("~"), ".ch_career_cache", "songs.sqlite")
        self.worker = ScanWorker(self.root_folder, cache_db)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.message.connect(self.progress.setLabelText)
        self.worker.done.connect(self._scan_finished)
        self.worker.done.connect(self.thread.quit)
        self.worker.done.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.progress.canceled.connect(self.worker.stop)

        self.thread.start()
        self.progress.show()

    def _scan_finished(self, songs: List[Song]):
        self.library = songs
        self._refresh_library_view()
        self.progress.close()
        QMessageBox.information(self, "Scan complete", f"Found {len(songs)} eligible songs.")

    def auto_arrange(self):
        if not self.library:
            QMessageBox.warning(self, "No library", "Scan your library first.")
            return
        n_tiers = self.spin_tiers.value()
        songs_per = self.spin_songs_per.value()
        tiers = auto_tier(
            self.library,
            n_tiers,
            songs_per,
            enforce_artist_limit=self.chk_artistlimit.isChecked(),
            keep_very_long_out_of_first_two=self.chk_longrule.isChecked(),
            shuffle_seed=None,
        )
        for i, w in enumerate(self.tiers_widgets):
            w.clear()
            for s in tiers[i]:
                item = self._build_song_item(s)
                w.addItem(item)
            self._sync_tier_height(w)
        self._sync_all_tier_heights()

    def export_now(self):
        tiers_songs: List[List[Song]] = []
        for w in self.tiers_widgets:
            tier_list: List[Song] = []
            for i in range(w.count()):
                s: Song = w.item(i).data(Qt.UserRole)
                tier_list.append(s)
            tiers_songs.append(tier_list)

        total_songs = sum(len(t) for t in tiers_songs)
        if total_songs == 0:
            QMessageBox.warning(self, "Empty setlist", "Add songs to tiers before exporting.")
            return

        choice = QMessageBox.question(
            self,
            "Export mode",
            "Export one .setlist per tier (recommended)?\nChoose 'No' to export a single combined setlist.",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if choice == QMessageBox.Cancel:
            return

        if choice == QMessageBox.No:
            out_path, _ = QFileDialog.getSaveFileName(self, "Save setlist", "career.setlist", "Clone Hero setlist (*.setlist)")
            if not out_path:
                return
            if os.path.exists(out_path):
                res = QMessageBox.question(self, "Overwrite?", f"{out_path} exists. Overwrite?", QMessageBox.Yes|QMessageBox.No)
                if res != QMessageBox.Yes:
                    return
            ordered: List[Song] = [s for tier in tiers_songs for s in tier]
            try:
                export_setlist_binary(ordered, out_path)
                md5s = read_setlist_md5s(out_path)
                if len(md5s) != len(ordered):
                    raise RuntimeError("Entry count mismatch on validation read-back")
            except Exception as e:
                QMessageBox.critical(self, "Export failed", f"{e}")
                return
            QMessageBox.information(self, "Export complete", f"Wrote combined .setlist ({len(ordered)} songs) to:\n{out_path}")
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Pick folder to save tier setlists")
        if not out_dir:
            return
        theme = self.theme_combo.currentText()
        written = 0
        for idx, songs in enumerate(tiers_songs):
            if not songs:
                continue
            name = tier_name_for(idx, theme)
            fname = f"{idx+1:02d} - {name}.setlist"
            path = os.path.join(out_dir, fname)
            if os.path.exists(path):
                res = QMessageBox.question(self, "Overwrite?", f"{path} exists. Overwrite?", QMessageBox.Yes|QMessageBox.No)
                if res != QMessageBox.Yes:
                    continue
            try:
                export_setlist_binary(songs, path)
                md5s = read_setlist_md5s(path)
                if len(md5s) != len(songs):
                    raise RuntimeError("Entry count mismatch on validation read-back")
                written += 1
            except Exception as e:
                QMessageBox.critical(self, "Export failed", f"{e}")
                return
        QMessageBox.information(self, "Export complete", f"Wrote {written} tier .setlist file(s) to:\n{out_dir}\nTotal songs: {total_songs}")
        return


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())



