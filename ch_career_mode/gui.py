"""Qt GUI for scanning libraries, arranging tiers, and exporting setlists."""

import math
import os
import random
import time
from typing import List, Optional
from dataclasses import replace

from PySide6.QtCore import Qt, QSize, QSettings, QThread
from PySide6.QtGui import QColor
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
    QFrame,
    QGraphicsDropShadowEffect,
)

from .core import Song, strip_color_tags, effective_score, effective_diff
from .scanner import ScanWorker, get_cache_path
from .tiering import auto_tier
from .exporter import export_setlist_binary, read_setlist_md5s

MEME_GENRES = {
    "meme",
    "memes",
    "heavy memes",
    "meme mashup",
    "nu-disco meme",
    "drum & bass meme",
}




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
    """Return a deterministic procedural tier name for index *i*."""
    a = PROCEDURAL_ADJS[i % len(PROCEDURAL_ADJS)]
    n = PROCEDURAL_NOUNS[i % len(PROCEDURAL_NOUNS)]
    return f"{a} {n}"


def tier_name_for(i: int, theme: str) -> str:
    """Resolve a tier name based on the configured theme."""
    names = THEME_SETS.get(theme)
    if names:
        return names[i] if i < len(names) else f"Tier {i+1}"
    if theme and theme.lower().startswith("procedural"):
        return _procedural_name(i)
    return f"Tier {i+1}"


LIBRARY_LIST_STYLE = """
QListWidget {
    border: 1px solid #2c2c2c;
    padding: 2px;
    background-color: #1a1a1a;
    color: #f0f0f0;
}
QListWidget::item {
    padding: 2px 6px;
}
QListWidget::item:selected {
    background-color: #3c3c3c;
}
"""

TIER_LIST_STYLE = """
QListWidget#tierList {
    border: none;
    padding: 4px 0;
    background-color: transparent;
    color: #f5f5f5;
}
QListWidget#tierList::item {
    padding: 4px 10px;
}
QListWidget#tierList::item:alternate {
    background-color: rgba(255, 255, 255, 0.05);
}
QListWidget#tierList::item:selected {
    background-color: rgba(255, 255, 255, 0.14);
}
"""

TIER_CARD_STYLE = """
QFrame#tierCard {
    background-color: #1b1d22;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
QWidget#tierHeader {
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}
QLabel#tierTitle {
    font-weight: 600;
    color: #f8f9fa;
}
"""

TIER_HEADER_COLORS = [
    "#ff6b35",
    "#f7b801",
    "#6a994e",
    "#386fa4",
    "#a267ac",
    "#ef476f",
]


class CompactItemDelegate(QStyledItemDelegate):
    """Item delegate that keeps QListWidget rows compact."""

    def __init__(self, vertical_padding: int = 2, parent=None):
        """Store the desired vertical padding for compact rows."""
        super().__init__(parent)
        self.vertical_padding = max(0, vertical_padding)

    def sizeHint(self, option, index):  # type: ignore[override]
        """Report a reduced-height size hint based on delegate padding."""
        size = super().sizeHint(option, index)
        fm_height = option.fontMetrics.height()
        size.setHeight(fm_height + self.vertical_padding * 2)
        return size


class TierList(QListWidget):
    """List widget used for tiers with optional drag-and-drop support."""
    def __init__(self, title: str, drop_handler=None):
        """Initialise the list and record an optional external drop handler."""
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        inner_min = max(200, TIER_COLUMN_MIN_WIDTH - 16)
        self.setMinimumWidth(inner_min)
        self.title = title
        self.title_label: Optional[QLabel] = None
        self._external_drop_handler = drop_handler

    def set_title(self, title: str) -> None:
        """Update both the stored title and any associated label widget."""
        self.title = title
        if self.title_label is not None:
            self.title_label.setText(title)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """Return a sensible default size for the tier column."""
        return QSize(220, 360)

    def _accepts_external_drag(self, event) -> bool:
        """Return True when the drag originates from the library list."""
        source = event.source()
        return (
            self._external_drop_handler is not None
            and isinstance(source, QListWidget)
            and getattr(source, "library_source", False)
        )

    def dragEnterEvent(self, event):
        """Accept drags from the library; defer others to the default handler."""
        if self._accepts_external_drag(event):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """Keep the move cursor active while a valid drag hovers."""
        if self._accepts_external_drag(event):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if self._accepts_external_drag(event):
            source = event.source()
            songs = []
            for item in source.selectedItems():
                song = item.data(Qt.UserRole)
                if song:
                    songs.append(song)
            if songs:
                event.setDropAction(Qt.CopyAction)
                self._external_drop_handler(self, songs)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class MainWindow(QMainWindow):
    """Main application window coordinating scans, tiering, and exports."""
    def __init__(self):
        """Bootstrap widgets, restore persisted settings, and prep defaults."""
        super().__init__()
        self.setWindowTitle("Clone Hero Career Builder")
        self.resize(DEFAULT_WINDOW_SIZE)

        self.settings = QSettings("CHCareer", "Builder")

        saved_root = self.settings.value("root_folder", None, type=str)
        self.root_folder: Optional[str] = saved_root if saved_root and os.path.isdir(saved_root) else None
        if saved_root and not self.root_folder:
            self.settings.remove("root_folder")

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
        self.btn_clear_cache = QPushButton("Clear Cache")
        self.btn_clear_cache.setToolTip("Deletes the songs cache so the library will be rebuilt on next scan.")

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
        exclude_memes_setting = bool(self.settings.value("exclude_memes", False, type=bool))
        self.chk_exclude_meme = QCheckBox("Exclude meme songs")
        self.chk_exclude_meme.setChecked(exclude_memes_setting)
        lower_official_setting = bool(self.settings.value("lower_official", False, type=bool))
        self.chk_lower_official = QCheckBox("Lower official chart difficulty")
        self.chk_lower_official.setChecked(lower_official_setting)
        self.chk_lower_official.setToolTip("Treats Harmonix/Neversoft charts as 1 step easier when scoring difficulty.")
        weight_by_nps_setting = bool(self.settings.value("weight_by_nps", False, type=bool))
        self.chk_weight_nps = QCheckBox("Weight Difficulty by NPS")
        self.chk_weight_nps.setChecked(weight_by_nps_setting)
        self.chk_weight_nps.setToolTip("Adds Avg/Peak NPS to the difficulty score when enabled.")
        saved_artist_limit = int(self.settings.value("artist_limit", 1)) if self.settings.contains("artist_limit") else 1
        self.spin_artist_limit = QSpinBox()
        self.spin_artist_limit.setRange(1, 10)
        self.spin_artist_limit.setValue(max(1, min(10, saved_artist_limit)))
        self.spin_min_diff = QSpinBox()
        self.spin_min_diff.setRange(1, 5)
        saved_min_diff = int(self.settings.value("min_difficulty", 1)) if self.settings.contains("min_difficulty") else 1
        self.spin_min_diff.setValue(max(1, min(5, saved_min_diff)))


        self.folder_status_indicator = QLabel()
        self.folder_status_indicator.setFixedSize(12, 12)
        self.folder_status_label = QLabel("(none)")
        self.folder_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        group_genre_setting = bool(self.settings.value("group_by_genre", False, type=bool))
        self.chk_group_genre = QCheckBox("Group songs in tiers by genre")
        self.chk_group_genre.setChecked(group_genre_setting)

        artist_mode_setting = bool(self.settings.value("artist_career_mode", False, type=bool))
        if not artist_mode_setting and self.settings.contains("filter_setlist"):
            artist_mode_setting = bool(self.settings.value("filter_setlist", False, type=bool))
            self.settings.setValue("artist_career_mode", artist_mode_setting)
            self.settings.remove("filter_setlist")
        self.chk_artist_career_mode = QCheckBox("Artist career mode")
        self.chk_artist_career_mode.setToolTip(
            "When enabled, Auto-Arrange builds tiers only from songs where the Artist tag matches the current search."
        )
        self.chk_artist_career_mode.setChecked(artist_mode_setting)

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
        self.lib_list.setDragDropMode(QAbstractItemView.DragOnly)
        self.lib_list.setDefaultDropAction(Qt.CopyAction)
        self.lib_list.setAcceptDrops(False)
        self.lib_list.library_source = True
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
        form.addRow(self.btn_clear_cache)
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(6)
        status_widget = QWidget()
        status_widget.setLayout(status_row)
        status_row.addWidget(self.folder_status_indicator)
        status_row.addWidget(self.folder_status_label, 1)
        form.addRow(status_widget)
        self._update_folder_status()
        form.addRow(QLabel("Tiers:"), self.spin_tiers)
        form.addRow(QLabel("Songs per tier:"), self.spin_songs_per)
        form.addRow(self.chk_longrule)
        form.addRow(self.chk_group_genre)

        form.addRow(self.chk_artist_career_mode)

        form.addRow(self.chk_exclude_meme)
        form.addRow(self.chk_lower_official)
        form.addRow(self.chk_weight_nps)
        self.lbl_artist_limit = QLabel("Max tracks by artist per tier:")
        form.addRow(self.lbl_artist_limit, self.spin_artist_limit)
        form.addRow(QLabel("Minimum Difficulty:"), self.spin_min_diff)
        form.addRow(QLabel("Theme:"), self.theme_combo)
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
        library_label = QLabel("Library")
        left_box.addWidget(library_label)
        self.search_box.setClearButtonEnabled(True)
        left_box.addWidget(self.search_box)
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
        self.btn_clear_cache.clicked.connect(self.clear_cache)
        self.spin_tiers.valueChanged.connect(self._on_tier_count_changed)
        self.search_box.textChanged.connect(self._refresh_library_view)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        self.chk_group_genre.stateChanged.connect(self._on_group_genre_changed)
        self.chk_artist_career_mode.stateChanged.connect(self._on_artist_career_mode_changed)
        self.chk_exclude_meme.stateChanged.connect(self._on_exclude_meme_changed)
        self.chk_lower_official.stateChanged.connect(self._on_lower_official_changed)
        self.chk_weight_nps.stateChanged.connect(self._on_weight_by_nps_changed)
        self.spin_artist_limit.valueChanged.connect(self._on_artist_limit_changed)
        self.spin_min_diff.valueChanged.connect(self._on_min_difficulty_changed)

        self._apply_artist_mode_state()

    def _lower_official_enabled(self) -> bool:
        """Return whether official Harmonix/Neversoft charts should be adjusted."""
        return self.chk_lower_official.isChecked()

    def _weight_by_nps_enabled(self) -> bool:
        """Return whether difficulty scores should include NPS weighting."""
        return self.chk_weight_nps.isChecked()


    def _update_size_constraints(self) -> None:
        """Enforce minimum widget sizes so the layout remains usable."""
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
        """Return True when the active theme should auto-generate tier names."""
        theme = self.theme_combo.currentText() if hasattr(self, "theme_combo") else ""
        return bool(theme) and theme.lower().startswith("procedural")

    def _generate_procedural_names(self, count: int) -> List[str]:
        """Produce deterministic pseudo-random tier names."""
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
        """Update the tier-name cache based on the current theme selection."""
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

    def _update_folder_status(self) -> None:
        """Refresh the library folder indicator and tooltip."""
        valid_path = self.root_folder if self.root_folder and os.path.isdir(self.root_folder) else None
        color = "#3CC13B" if valid_path else "#D9534F"
        self.folder_status_indicator.setStyleSheet(
            f"background-color: {color}; border: 1px solid #222; border-radius: 6px;"
        )
        display_text = valid_path or "(none)"
        metrics = self.folder_status_label.fontMetrics()
        elided = metrics.elidedText(display_text, Qt.ElideMiddle, 260)
        self.folder_status_label.setText(elided)
        self.folder_status_label.setToolTip(display_text)
    
    def _update_tier_titles(self) -> None:
        """Sync each tier widget caption with the latest names."""
        for idx, tier in enumerate(self.tiers_widgets):
            tier.set_title(self._tier_name(idx))

    def _tier_name(self, idx: int) -> str:
        """Return a tier name for the index, falling back to numbering."""
        if 0 <= idx < len(self.current_tier_names):
            return self.current_tier_names[idx]
        theme = self.theme_combo.currentText() if hasattr(self, "theme_combo") else ""
        return tier_name_for(idx, theme)

    def _on_theme_changed(self, theme: str) -> None:
        """Persist the theme selection and regenerate tier names."""
        self.settings.setValue("tier_theme", theme)
        self._regenerate_tier_names(procedural_refresh=True)
        self._update_tier_titles()
        self._update_size_constraints()

    def _on_group_genre_changed(self, state: int) -> None:
        """Store the genre-group toggle and refresh the library if needed."""
        self.settings.setValue("group_by_genre", state == Qt.Checked)
        self.settings.sync()

    def _on_artist_career_mode_changed(self, state: int) -> None:
        """Persist the artist-career-mode toggle and refresh dependent UI."""
        self.settings.setValue("artist_career_mode", state == Qt.Checked)
        self._apply_artist_mode_state()

    def _on_exclude_meme_changed(self, state: int) -> None:
        """Persist the meme filter toggle and refresh the library view."""
        self.settings.setValue("exclude_memes", state == Qt.Checked)
        self._refresh_library_view()

    def _on_lower_official_changed(self, state: int) -> None:
        """Persist the Harmonix/Neversoft adjustment preference and refresh."""
        self.settings.setValue("lower_official", state == Qt.Checked)
        self._refresh_library_view()
        self._refresh_tier_tooltips()

    def _on_weight_by_nps_changed(self, state: int) -> None:
        """Persist the NPS weighting preference and refresh relevant views."""
        self.settings.setValue("weight_by_nps", state == Qt.Checked)
        self._refresh_library_view()
        self._refresh_tier_tooltips()

    def _on_artist_limit_changed(self, value: int) -> None:
        """Save the per-artist cap and refresh the library preview."""
        self.settings.setValue("artist_limit", value)
        self._refresh_library_view()

    def _apply_artist_mode_state(self) -> None:
        """Enable/disable controls tied to artist-career mode and refresh."""
        if not hasattr(self, "chk_artist_career_mode"):
            return
        artist_mode = self.chk_artist_career_mode.isChecked()
        self.spin_artist_limit.setEnabled(not artist_mode)
        if hasattr(self, "lbl_artist_limit"):
            self.lbl_artist_limit.setEnabled(not artist_mode)
        self._refresh_library_view()

    def _on_min_difficulty_changed(self, value: int) -> None:
        """Persist the minimum difficulty threshold and refresh the list."""
        self.settings.setValue("min_difficulty", value)
        self._refresh_library_view()

    def _on_tier_count_changed(self, value: int) -> None:
        """Rebuild the tier widgets when the tier count changes."""
        self._regenerate_tier_names(procedural_refresh=self._is_procedural_theme())
        self._rebuild_tier_widgets()

    def _apply_compact_list_style(self, widget: QListWidget, variant: str = "library") -> CompactItemDelegate:
        """Attach the compact delegate and configure shared list settings."""
        if variant == "tier":
            widget.setObjectName("tierList")
            widget.setStyleSheet(TIER_LIST_STYLE)
            widget.setSpacing(0)
            widget.setAlternatingRowColors(True)
        else:
            widget.setStyleSheet(LIBRARY_LIST_STYLE)
            widget.setSpacing(1)
            widget.setAlternatingRowColors(False)
        widget.setFrameShape(QFrame.NoFrame)
        widget.setUniformItemSizes(True)
        widget.setSizeAdjustPolicy(QAbstractItemView.AdjustToContents)
        widget.setWordWrap(False)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        delegate = CompactItemDelegate(1, widget)
        widget.setItemDelegate(delegate)
        return delegate

    def _rebuild_tier_widgets(self) -> None:
        """Create the tier list widgets according to the current tier count."""
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
            tier = TierList(self._tier_name(idx), drop_handler=self._handle_library_drop)
            tier.itemDoubleClicked.connect(lambda item, t=tier: self._remove_from_tier(t, item))
            self._list_delegates.append(self._apply_compact_list_style(tier, variant="tier"))

            wrapper = self._create_tier_panel(tier, idx)
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

    def _create_tier_panel(self, tier: TierList, index: int) -> QWidget:
        """Wrap a tier list with a captioned container for display."""
        panel = QFrame()
        panel.setObjectName("tierCard")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        panel.setStyleSheet(TIER_CARD_STYLE)

        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 110))
        panel.setGraphicsEffect(shadow)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("tierHeader")
        header_color = TIER_HEADER_COLORS[index % len(TIER_HEADER_COLORS)]
        header.setStyleSheet(
            f"background-color: {header_color}; border-top-left-radius: 12px; border-top-right-radius: 12px;"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(0)

        title = QLabel(tier.title)
        title.setObjectName("tierTitle")
        title.setAlignment(Qt.AlignHCenter)
        header_layout.addWidget(title)
        layout.addWidget(header)
        tier.title_label = title

        tier.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tier.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(tier)
        return panel

    def _sync_tier_height(self, tier: TierList) -> None:
        """Resize a tier to show the configured number of rows."""
        target_rows = max(self.spin_songs_per.value(), tier.count())
        height = self._tier_height_for(tier, target_rows)
        tier.setFixedHeight(height)
        parent = tier.parentWidget()
        if parent:
            parent.updateGeometry()

    def _tier_height_for(self, tier: QListWidget, rows: int) -> int:
        """Compute the pixel height needed to display *rows* entries."""
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
        """Synchronise every tier list height after content changes."""
        for tier in self.tiers_widgets:
            self._sync_tier_height(tier)
        self._update_size_constraints()

    def _remove_from_tier(self, tier_widget: TierList, item: QListWidgetItem) -> None:
        """Remove a song from a tier and return it to the library pane."""
        tier_widget.takeItem(tier_widget.row(item))
        self._sync_tier_height(tier_widget)
        self._sync_all_tier_heights()

    def _handle_library_drop(self, tier_widget: TierList, songs: List[Song]) -> None:
        """Add dropped library songs to a tier while respecting filters."""
        lower_official = self._lower_official_enabled()
        for song in songs:
            effective = effective_diff(song, lower_official) or 0
            if effective < self.spin_min_diff.value():
                continue
            if self.chk_exclude_meme.isChecked() and (song.genre or "").strip().lower() in MEME_GENRES:
                continue
            item = self._build_song_item(song)
            tier_widget.addItem(item)
        self._sync_tier_height(tier_widget)
        self._sync_all_tier_heights()

    def _format_length(self, song: Song) -> Optional[str]:
        """Return an mm:ss string for the song length when available."""

        if song.length_ms is None or song.length_ms < 0:
            return None
        mins = song.length_ms // 60000
        secs = (song.length_ms // 1000) % 60
        return f"{mins}:{secs:02d}"

    def _format_nps_value(self, value: float) -> str:
        """Format an NPS value, trimming unnecessary trailing zeros."""

        text = f"{value:.1f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    def _compose_song_tooltip(
        self,
        song: Song,
        *,
        length_str: Optional[str] = None,
        display_artist: Optional[str] = None,
        display_charter: Optional[str] = None,
        display_genre: Optional[str] = None,
        lower_official: Optional[bool] = None,
        weight_by_nps: Optional[bool] = None,
    ) -> str:
        """Build the tooltip text showing song metadata and scoring details."""

        if length_str is None:
            length_str = self._format_length(song)
        if display_artist is None:
            display_artist = strip_color_tags(song.artist)
        if display_genre is None:
            display_genre = strip_color_tags(song.genre) if getattr(song, "genre", "") else ""
        if display_charter is None:
            display_charter = strip_color_tags(song.charter)
        if lower_official is None:
            lower_official = self._lower_official_enabled()
        if weight_by_nps is None:
            weight_by_nps = self._weight_by_nps_enabled()

        details = []
        if display_artist:
            details.append(f"Artist: {display_artist}")
        if display_genre:
            details.append(f"Genre: {display_genre}")
        if display_charter:
            details.append(f"Charter: {display_charter}")
        adj_diff = effective_diff(song, lower_official)
        difficulty_text = f"D{adj_diff}" if adj_diff is not None else "Unknown"
        details.append(f"Difficulty: {difficulty_text}")
        score_value = int(effective_score(song, lower_official, weight_by_nps=weight_by_nps))
        details.append(f"Score: {score_value}")
        if length_str:
            details.append(f"Length: {length_str}")
        avg = getattr(song, "nps_avg", 0.0) or 0.0
        peak = getattr(song, "nps_peak", 0.0) or 0.0
        details.append(f"Avg NPS: {self._format_nps_value(avg)}")
        details.append(f"Peak NPS: {self._format_nps_value(peak)}")
        return "\n".join(details)

    def _build_song_item(self, song: Song) -> QListWidgetItem:
        """Create a list item with display text and metadata tooltip."""

        length_str = self._format_length(song)
        display_name = strip_color_tags(song.name)
        display_artist = strip_color_tags(song.artist)
        display_charter = strip_color_tags(song.charter)
        display_genre = strip_color_tags(song.genre) if getattr(song, "genre", "") else ""

        artist_segment = f" - {display_artist}" if display_artist else ""
        length_segment = f" [{length_str}]" if length_str else ""
        item = QListWidgetItem(f"{display_name}{artist_segment}{length_segment}")

        tooltip = self._compose_song_tooltip(
            song,
            length_str=length_str,
            display_artist=display_artist,
            display_charter=display_charter,
            display_genre=display_genre,
            lower_official=self._lower_official_enabled(),
            weight_by_nps=self._weight_by_nps_enabled(),
        )
        item.setToolTip(tooltip)
        item.setData(Qt.UserRole, song)
        return item


    def _eligible_library_songs(self, apply_search_filter: bool, *, query_mode: str = "library") -> List[Song]:

        """Return songs passing library filters, optionally narrowed by search."""
        if not self.library:
            return []

        lower_official = self._lower_official_enabled()
        weight_by_nps = self._weight_by_nps_enabled()
        min_diff = self.spin_min_diff.value() if hasattr(self, "spin_min_diff") else 1
        exclude_memes = self.chk_exclude_meme.isChecked() if hasattr(self, "chk_exclude_meme") else False
        query = ""
        if apply_search_filter and hasattr(self, "search_box"):
            query = self.search_box.text().casefold().strip()


        def matches_query(song: Song) -> bool:
            if not query:
                return True
            artist = (song.artist or "").casefold()
            if query_mode == "artist_only":
                return query in artist
            name = (song.name or "").casefold()
            charter = (song.charter or "").casefold()
            return query in name or query in artist or query in charter

        filtered: List[Song] = []
        for song in self.library:
            effective = effective_diff(song, lower_official) or 0
            if effective < min_diff:
                continue
            genre_key = (song.genre or "").strip().lower()
            if exclude_memes and genre_key in MEME_GENRES:
                continue
            if apply_search_filter and not matches_query(song):
                continue
            filtered.append(song)

        filtered.sort(
            key=lambda song: (
                effective_score(song, lower_official, weight_by_nps=weight_by_nps),
                (song.name or "").lower(),
            )
        )
        return filtered

    def _refresh_library_view(self) -> None:
        """Populate the library list according to the active filters."""
        self.lib_list.clear()
        artist_toggle = getattr(self, "chk_artist_career_mode", None)
        query_mode = "artist_only" if artist_toggle and artist_toggle.isChecked() else "library"
        for s in self._eligible_library_songs(apply_search_filter=True, query_mode=query_mode):
            item = self._build_song_item(s)
            self.lib_list.addItem(item)

    def _refresh_tier_tooltips(self) -> None:
        """Update tier item tooltips to reflect current scoring preferences."""

        if not getattr(self, "tiers_widgets", None):
            return
        lower_official = self._lower_official_enabled()
        weight_by_nps = self._weight_by_nps_enabled()
        for tier in self.tiers_widgets:
            for row in range(tier.count()):
                item = tier.item(row)
                song = item.data(Qt.UserRole)
                if isinstance(song, Song):
                    tooltip = self._compose_song_tooltip(
                        song,
                        lower_official=lower_official,
                        weight_by_nps=weight_by_nps,
                    )
                    item.setToolTip(tooltip)

    def pick_folder(self) -> None:
        """Prompt the user to select a Clone Hero songs directory."""
        initial_dir = self.root_folder if self.root_folder and os.path.isdir(self.root_folder) else os.path.expanduser("~")
        d = QFileDialog.getExistingDirectory(self, "Pick top-level Clone Hero songs root", initial_dir)
        if d:
            self.root_folder = d
            self.settings.setValue("root_folder", d)
            self._update_folder_status()

    def clear_cache(self) -> None:
        """Allow the user to delete the cached song database."""

        choice = QMessageBox.question(
            self,
            "Clear Cache",
            "Are you sure you want to clear the cache? The library will need to be rescanned.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice != QMessageBox.Yes:
            return

        cache_path = get_cache_path(create=False)
        try:
            os.remove(cache_path)
            removed = True
        except FileNotFoundError:
            removed = False
        except OSError as exc:
            QMessageBox.warning(self, "Cache Error", f"Could not clear the cache.\n{exc}")
            return

        if removed or not os.path.exists(cache_path):
            QMessageBox.information(self, "Cache cleared", "The songs cache was cleared successfully.")

    def scan_now(self) -> None:
        """Start the asynchronous library scan with progress feedback."""
        if not self.root_folder or not os.path.isdir(self.root_folder):
            self.root_folder = None
            self.settings.remove("root_folder")
            self._update_folder_status()
            QMessageBox.warning(self, "No folder", "Please pick your TOP-LEVEL songs folder first.")
            return

        self.progress = QProgressDialog("Scanning songs...", "Cancel", 0, 100, self)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setAutoClose(True)
        self.progress.setMinimumDuration(0)

        self.thread = QThread(self)
        cache_db = get_cache_path()
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
        """Handle completion of the background scan and refresh the UI."""
        self.library = songs
        self._refresh_library_view()
        self.progress.close()
        QMessageBox.information(self, "Scan complete", f"Found {len(songs)} eligible songs.")

    def auto_arrange(self) -> None:
        """Generate a new set of tiers using the current configuration."""
        if not self.library:
            QMessageBox.warning(self, "No library", "Scan your library first.")
            return
        n_tiers = self.spin_tiers.value()
        songs_per = self.spin_songs_per.value()
        self._regenerate_tier_names(procedural_refresh=self._is_procedural_theme())

        use_artist_mode = self.chk_artist_career_mode.isChecked()
        songs = self._eligible_library_songs(
            apply_search_filter=use_artist_mode,
            query_mode="artist_only" if use_artist_mode else "library",
        )
        lower_official = self._lower_official_enabled()
        weight_by_nps = self._weight_by_nps_enabled()
        tier_candidates = [
            replace(
                s,
                diff_guitar=effective_diff(s, lower_official),
                score=effective_score(s, lower_official, weight_by_nps=weight_by_nps),
            )
            for s in songs
        ]
        if not tier_candidates:
            if use_artist_mode:
                QMessageBox.warning(
                    self,
                    "No songs meet criteria",
                    "No songs match the current search and filters. Adjust the search query or disable Artist career mode.",
                )
            else:
                QMessageBox.warning(
                    self,
                    "No songs meet criteria",
                    "Lower the minimum difficulty, allow meme songs, or scan more songs.",
                )
            return

        tiers = auto_tier(
            tier_candidates,
            n_tiers,
            songs_per,
            max_tracks_per_artist=0 if use_artist_mode else self.spin_artist_limit.value(),
            keep_very_long_out_of_first_two=self.chk_longrule.isChecked(),
            shuffle_seed=None,
            group_by_genre=self.chk_group_genre.isChecked(),
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
        """Export the arranged tiers to Clone Hero .setlist files."""
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


