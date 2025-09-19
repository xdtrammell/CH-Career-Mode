import math
import os
import random
import time
from typing import List, Optional

from PySide6.QtCore import Qt, QSize, QSettings, QThread
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QLineEdit,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QScrollArea,
    QComboBox,
    QProgressDialog,
    QStyledItemDelegate,
    QAbstractItemView,
    QGridLayout,
    QSizePolicy,
    QStyle,
)

from .core import Song, strip_color_tags
from .scanner import ScanWorker
from .tiering import auto_tier
from .exporter import export_setlist_binary, read_setlist_md5s


GH_TIER_NAMES = [
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
TIER_COLUMN_SPACING = 8
MAIN_LAYOUT_MARGIN = 8
MAIN_LAYOUT_SPACING = 12
LIBRARY_MIN_WIDTH = 300
SETTINGS_MIN_WIDTH = 280
TIER_COLUMN_MIN_WIDTH = 240
TIER_LIST_EXTRA_PADDING = 8
WINDOW_MIN_HEIGHT = 760
WINDOW_MIN_WIDTH = (
    LIBRARY_MIN_WIDTH
    + SETTINGS_MIN_WIDTH
    + TIER_COLUMNS * TIER_COLUMN_MIN_WIDTH
    + (TIER_COLUMNS - 1) * TIER_COLUMN_SPACING
    + 2 * MAIN_LAYOUT_SPACING
    + 2 * MAIN_LAYOUT_MARGIN
)
DEFAULT_WINDOW_SIZE = QSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)


THEME_SETS = {
    "Guitar Hero - Classic Venue Names": GH_TIER_NAMES,
    "Guitar Hero (2005) - Career Sets": [
        "Opening Licks",
        "Axe-Grinders",
        "Thrash and Burn",
        "Return of the Shred",
        "Relentless Riffs",
        "Furious Fretwork",
        "Face-Melters",
    ],
    "Guitar Hero II - Career Sets": [
        "Opening Licks",
        "Amp-Warmers",
        "String Snappers",
        "Thrash and Burn",
        "Return of the Shred",
        "Relentless Riffs",
        "Furious Fretwork",
        "Face-Melters",
    ],
}

PROCEDURAL_ADJS = [
    "Backroom",
    "Basement",
    "Neon",
    "Touring",
    "Midnight",
    "Electric",
    "Thunder",
    "Retro",
    "Steel",
    "Crimson",
    "Golden",
    "Wild",
    "Loud",
    "Feral",
    "Wired",
]
PROCEDURAL_NOUNS = [
    "Licks",
    "Amp Warmers",
    "Riff Run",
    "Shred Set",
    "Encore",
    "Stage Lights",
    "Roadshow",
    "Soundcheck",
    "Headliners",
    "Pit Crew",
    "Afterparty",
    "Finale",
]


def _procedural_name(i: int) -> str:
    a = PROCEDURAL_ADJS[i % len(PROCEDURAL_ADJS)]
    n = PROCEDURAL_NOUNS[i % len(PROCEDURAL_NOUNS)]
    return f"{a} {n}"


def tier_name_for(i: int, theme: str) -> str:
    names = THEME_SETS.get(theme)
    if names:
        return names[i] if i < len(names) else f"Tier {i+1}"
    if theme and theme.lower().startswith("procedural"):
        return _procedural_name(i)
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

    def sizeHint(self, option, index):  # type: ignore[override]
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
        inner_min = max(200, TIER_COLUMN_MIN_WIDTH - 16)
        self.setMinimumWidth(inner_min)
        self.title = title
        self.title_label: Optional[QLabel] = None

    def set_title(self, title: str) -> None:
        self.title = title
        if self.title_label is not None:
            self.title_label.setText(title)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(220, 360)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clone Hero Career Builder")
        self.resize(DEFAULT_WINDOW_SIZE)

        self.settings = QSettings("CHCareer", "Builder")

        self.library: List[Song] = []
        self.tiers_widgets: List[TierList] = []
        self.tier_wrappers: List[QWidget] = []
        self._list_delegates: List[CompactItemDelegate] = []
        self.current_tier_names: List[str] = []
        self._procedural_seed = None

        self.btn_pick = QPushButton("Pick Songs Folder...")
        self.btn_scan = QPushButton("Scan (recursive)")
        self.btn_auto = QPushButton("Auto-Arrange")
        self.btn_export = QPushButton("Export Setlist...")

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search title / artist / charter...")
        self.diff_min = QSpinBox()
        self.diff_min.setRange(0, 9)
        self.diff_min.setValue(0)
        self.diff_max = QSpinBox()
        self.diff_max.setRange(0, 9)
        self.diff_max.setValue(9)
        self.chk_longrule = QCheckBox("Keep >7:00 out of first two tiers")
        self.chk_longrule.setChecked(True)
        self.chk_artistlimit = QCheckBox("Max 1 per artist per tier")
        self.chk_artistlimit.setChecked(True)

        self.spin_tiers = QSpinBox()
        self.spin_tiers.setRange(1, 20)
        self.spin_tiers.setValue(6)
        self.spin_songs_per = QSpinBox()
        self.spin_songs_per.setRange(1, 10)
        self.spin_songs_per.setValue(5)
        self.spin_songs_per.valueChanged.connect(lambda _=None: self._sync_all_tier_heights())

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["None (Custom Tier Names)"] + list(THEME_SETS.keys()) + ["Procedural - Rock Tour"])
        saved_theme = self.settings.value("tier_theme", "Procedural - Rock Tour", type=str)
        available_themes = [self.theme_combo.itemText(i) for i in range(self.theme_combo.count())]
        if saved_theme not in available_themes:
            saved_theme = "Procedural - Rock Tour"
        self.theme_combo.setCurrentText(saved_theme)

        self.lib_list = QListWidget()
        self.lib_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.lib_list.setDragEnabled(True)
        self.lib_list.setDefaultDropAction(Qt.MoveAction)
        self._list_delegates.append(self._apply_compact_list_style(self.lib_list))

        self.tiers_container = QWidget()
        self.tiers_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.tiers_layout = QGridLayout(self.tiers_container)
        self.tiers_layout.setContentsMargins(0, 0, 0, 0)
        self.tiers_layout.setHorizontalSpacing(TIER_COLUMN_SPACING)
        self.tiers_layout.setVerticalSpacing(TIER_COLUMN_SPACING)
        self.tiers_layout.setAlignment(Qt.AlignTop)

        self.tiers_scroll = QScrollArea()
        self.tiers_scroll.setWidgetResizable(True)
        self.tiers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tiers_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tiers_scroll.setWidget(self.tiers_container)

        self._regenerate_tier_names(procedural_refresh=True)
        self._rebuild_tier_widgets()

        self.settings_box = QGroupBox("Settings")
        form = QFormLayout(self.settings_box)
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

        central = QWidget()
        self.setCentralWidget(central)
        h = QHBoxLayout(central)
        h.setContentsMargins(MAIN_LAYOUT_MARGIN, MAIN_LAYOUT_MARGIN, MAIN_LAYOUT_MARGIN, MAIN_LAYOUT_MARGIN)
        h.setSpacing(MAIN_LAYOUT_SPACING)
        self.main_layout = h

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
        h.addWidget(self.settings_box, 1)

        self._update_size_constraints()

        self.btn_pick.clicked.connect(self.pick_folder)
        self.btn_scan.clicked.connect(self.scan_now)
        self.btn_auto.clicked.connect(self.auto_arrange)
        self.btn_export.clicked.connect(self.export_now)
        self.spin_tiers.valueChanged.connect(self._on_tier_count_changed)
        self.search_box.textChanged.connect(self._refresh_library_view)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        self.root_folder: Optional[str] = self.settings.value("root_folder", None, type=str)

    def _update_size_constraints(self) -> None:
        if hasattr(self, 'lib_list'):
            self.lib_list.setMinimumWidth(LIBRARY_MIN_WIDTH)
        if hasattr(self, 'settings_box'):
            self.settings_box.setMinimumWidth(SETTINGS_MIN_WIDTH)
        if hasattr(self, 'tiers_scroll'):
            tiers_min_width = TIER_COLUMNS * TIER_COLUMN_MIN_WIDTH + (TIER_COLUMNS - 1) * TIER_COLUMN_SPACING
            self.tiers_scroll.setMinimumWidth(tiers_min_width)
        if hasattr(self, 'main_layout'):
            self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
            target_width = max(self.width(), WINDOW_MIN_WIDTH)
            target_height = max(self.height(), WINDOW_MIN_HEIGHT)
            if target_width != self.width() or target_height != self.height():
                self.resize(target_width, target_height)

    def _is_procedural_theme(self) -> bool:
        theme = self.theme_combo.currentText() if hasattr(self, "theme_combo") else ""
        return bool(theme) and theme.lower().startswith("procedural")

    def _generate_procedural_names(self, count: int) -> List[str]:
        combos = [f"{adj} {noun}" for adj in PROCEDURAL_ADJS for noun in PROCEDURAL_NOUNS]
        if not combos:
            return [f"Tier {i+1}" for i in range(count)]
        seed = time.time_ns()
        rnd = random.Random(seed)
        self._procedural_seed = seed
        if count <= len(combos):
            return rnd.sample(combos, count)
        rnd.shuffle(combos)
        selected: List[str] = []
        pool = combos.copy()
        while len(selected) < count:
            if not pool:
                pool = combos.copy()
                rnd.shuffle(pool)
            name = pool.pop()
            if name in selected:
                dup = sum(1 for n in selected if n.startswith(name)) + 1
                name = f"{name} #{dup}"
            selected.append(name)
        return selected

    def _regenerate_tier_names(self, procedural_refresh: bool = False) -> None:
        count = self.spin_tiers.value() if hasattr(self, "spin_tiers") else 0
        theme = self.theme_combo.currentText() if hasattr(self, "theme_combo") else ""
        if theme == "None (Custom Tier Names)":
            names = [f"Tier {i+1}" for i in range(count)]
        elif theme in THEME_SETS:
            base = THEME_SETS[theme]
            names = [base[i] if i < len(base) else f"Tier {i+1}" for i in range(count)]
        elif theme and theme.lower().startswith("procedural"):
            if procedural_refresh or len(self.current_tier_names) != count:
                names = self._generate_procedural_names(count)
            else:
                names = self.current_tier_names[:count]
        else:
            names = [f"Tier {i+1}" for i in range(count)]
        self.current_tier_names = names

    def _update_tier_titles(self) -> None:
        for idx, tier in enumerate(self.tiers_widgets):
            tier.set_title(self._tier_name(idx))

    def _tier_name(self, idx: int) -> str:
        if 0 <= idx < len(self.current_tier_names):
            return self.current_tier_names[idx]
        theme = self.theme_combo.currentText() if hasattr(self, "theme_combo") else ""
        return tier_name_for(idx, theme)

    def _on_theme_changed(self, theme: str) -> None:
        self.settings.setValue("tier_theme", theme)
        self._regenerate_tier_names(procedural_refresh=True)
        self._update_tier_titles()
        self._update_size_constraints()

    def _on_tier_count_changed(self, value: int) -> None:
        self._regenerate_tier_names(procedural_refresh=self._is_procedural_theme())
        self._rebuild_tier_widgets()

    def _apply_compact_list_style(self, widget: QListWidget) -> CompactItemDelegate:
        widget.setStyleSheet(COMPACT_LIST_STYLE)
        widget.setSpacing(1)
        widget.setUniformItemSizes(True)
        widget.setSizeAdjustPolicy(QAbstractItemView.AdjustToContents)
        widget.setWordWrap(False)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        delegate = CompactItemDelegate(1, widget)
        widget.setItemDelegate(delegate)
        return delegate

    def _rebuild_tier_widgets(self) -> None:
        self._list_delegates = self._list_delegates[:1]
        self._regenerate_tier_names()
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
            tier = TierList(self._tier_name(idx))
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
        self._update_tier_titles()
        if hasattr(self, "settings_box"):
            self._update_size_constraints()

    def _create_tier_panel(self, tier: TierList) -> QWidget:
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        title = QLabel(tier.title)
        title.setAlignment(Qt.AlignHCenter)
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        tier.title_label = title

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

        delegate = tier.itemDelegate()
        row_height = tier.sizeHintForRow(0) if tier.count() else 0
        if row_height <= 0 and hasattr(delegate, "vertical_padding"):
            row_height = tier.fontMetrics().height() + delegate.vertical_padding * 2
        if row_height <= 0 and self.lib_list.count():
            row_height = self.lib_list.sizeHintForRow(0)
        if row_height <= 0:
            row_height = tier.fontMetrics().height() + 6

        spacing = tier.spacing()
        frame = tier.frameWidth() * 2
        style_margin = tier.style().pixelMetric(QStyle.PM_FocusFrameVMargin, None, tier)
        total_rows = rows
        return (
            total_rows * row_height
            + max(0, total_rows - 1) * spacing
            + frame
            + style_margin * 2
            + TIER_LIST_EXTRA_PADDING
        )

    def _sync_all_tier_heights(self) -> None:
        for tier in self.tiers_widgets:
            self._sync_tier_height(tier)
        self._update_size_constraints()

    def _remove_from_tier(self, tier_widget: TierList, item: QListWidgetItem) -> None:
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

        display_name = strip_color_tags(song.name)
        display_artist = strip_color_tags(song.artist)
        display_charter = strip_color_tags(song.charter)

        artist_segment = f" - {display_artist}" if display_artist else ""
        length_segment = f" [{length_str}]" if length_str else ""
        item = QListWidgetItem(f"{display_name}{artist_segment}{length_segment}")

        details = []
        if display_artist:
            details.append(f"Artist: {display_artist}")
        if display_charter:
            details.append(f"Charter: {display_charter}")
        difficulty_text = f"D{song.diff_guitar}" if song.diff_guitar is not None else "Unknown"
        details.append(f"Difficulty: {difficulty_text}")
        details.append(f"Score: {int(song.score)}")
        if length_str:
            details.append(f"Length: {length_str}")
        item.setToolTip("\n".join(details))
        item.setData(Qt.UserRole, song)
        return item

    def _refresh_library_view(self) -> None:
        q = self.search_box.text().lower().strip()
        self.lib_list.clear()
        for s in sorted(self.library, key=lambda s: (s.score, s.name.lower())):
            if q and q not in s.name.lower() and q not in s.artist.lower() and q not in s.charter.lower():
                continue
            item = self._build_song_item(s)
            self.lib_list.addItem(item)

    def pick_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Pick top-level Clone Hero songs root")
        if d:
            self.root_folder = d
            self.settings.setValue("root_folder", d)

    def scan_now(self) -> None:
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

    def _scan_finished(self, songs: List[Song]) -> None:
        self.library = songs
        self._refresh_library_view()
        self.progress.close()
        QMessageBox.information(self, "Scan complete", f"Found {len(songs)} eligible songs.")

    def auto_arrange(self) -> None:
        if not self.library:
            QMessageBox.warning(self, "No library", "Scan your library first.")
            return
        n_tiers = self.spin_tiers.value()
        songs_per = self.spin_songs_per.value()
        self._regenerate_tier_names(procedural_refresh=self._is_procedural_theme())

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
            tier_songs = sorted(
                tiers[i],
                key=lambda song: (
                    song.score,
                    song.length_ms if song.length_ms is not None else float("inf"),
                    song.name.lower(),
                ),
            )
            for s in tier_songs:
                item = self._build_song_item(s)
                w.addItem(item)
            self._sync_tier_height(w)
        self._update_tier_titles()
        self._sync_all_tier_heights()

    def export_now(self) -> None:
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
            out_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save setlist",
                "career.setlist",
                "Clone Hero setlist (*.setlist)",
            )
            if not out_path:
                return
            if os.path.exists(out_path):
                res = QMessageBox.question(self, "Overwrite?", f"{out_path} exists. Overwrite?", QMessageBox.Yes | QMessageBox.No)
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
            QMessageBox.information(
                self,
                "Export complete",
                f"Wrote combined .setlist ({len(ordered)} songs) to:\n{out_path}",
            )
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Pick folder to save tier setlists")
        if not out_dir:
            return
        written = 0
        for idx, songs in enumerate(tiers_songs):
            if not songs:
                continue
            name = self._tier_name(idx)
            fname = f"{idx+1:02d} - {name}.setlist"
            path = os.path.join(out_dir, fname)
            if os.path.exists(path):
                res = QMessageBox.question(self, "Overwrite?", f"{path} exists. Overwrite?", QMessageBox.Yes | QMessageBox.No)
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
        QMessageBox.information(
            self,
            "Export complete",
            f"Wrote {written} tier .setlist file(s) to:\n{out_dir}\nTotal songs: {total_songs}",
        )

