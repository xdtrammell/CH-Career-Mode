"""Qt GUI for scanning libraries, arranging tiers, and exporting setlists."""

import math
import os
import random
import time
from typing import Dict, List, Optional
from dataclasses import replace

from PySide6.QtCore import (
    Qt,
    QSize,
    QSettings,
    QThread,
    QTimer,
    QMargins,
    Signal,
    QEasingCurve,
    QVariantAnimation,
)
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
    QFormLayout,
    QMessageBox,
    QScrollArea,
    QComboBox,
    QStyledItemDelegate,
    QAbstractItemView,
    QGridLayout,
    QSizePolicy,
    QStyle,
QFrame,
QGraphicsDropShadowEffect,
QProgressBar,
QToolBox,
QToolButton,
QScrollBar,
QLayout,
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
TIER_GRID_LAYOUT_MARGIN = 8
MAIN_LAYOUT_MARGIN = 8
MAIN_LAYOUT_SPACING = 12
LIBRARY_MIN_WIDTH = 300
SETTINGS_MIN_WIDTH = 280
TIER_COLUMN_MIN_WIDTH = 240
TIER_LIST_EXTRA_PADDING = 8
TIER_SCROLL_GUTTER_WIDTH = 12
EXTERNAL_VBAR_WIDTH = 12
CARD_CONTENT_MARGIN = 18
CARD_CONTENT_PADDING = CARD_CONTENT_MARGIN * 2
WINDOW_MIN_HEIGHT = 760
LIBRARY_PANEL_MIN_WIDTH = LIBRARY_MIN_WIDTH + CARD_CONTENT_PADDING
TIERS_PANEL_MIN_WIDTH = (
    TIER_COLUMNS * TIER_COLUMN_MIN_WIDTH
    + (TIER_COLUMNS - 1) * TIER_COLUMN_SPACING
    + CARD_CONTENT_PADDING
    + 2 * TIER_GRID_LAYOUT_MARGIN
    + TIER_SCROLL_GUTTER_WIDTH
    + EXTERNAL_VBAR_WIDTH
)
WINDOW_MIN_WIDTH = (
    LIBRARY_PANEL_MIN_WIDTH
    + SETTINGS_MIN_WIDTH
    + TIERS_PANEL_MIN_WIDTH
    + 2 * MAIN_LAYOUT_SPACING
    + 2 * MAIN_LAYOUT_MARGIN
)
DEFAULT_WINDOW_SIZE = QSize(WINDOW_MIN_WIDTH + 40, WINDOW_MIN_HEIGHT)


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


ACCENT_COLOR = "#5e81ff"
ACCENT_COLOR_HOVER = "#7b96ff"
SURFACE_COLOR = "#181b23"
SURFACE_ELEVATED = "#1f2633"
SCAN_PHASE1_COLOR = "#5A73FF"
SCAN_PHASE2_COLOR = "#9E6FFF"
SCAN_PHASE_HEADER_COLOR = "#A5D6FF"
SCAN_COLOR_ANIM_DURATION_MS = 350

SCAN_IDLE = "idle"
SCAN_PHASE1 = "phase1"
SCAN_PHASE2 = "phase2"
SCAN_COMPLETE = "complete"
SCAN_CANCELLED = "cancelled"
SCAN_ERROR = "error"

APP_STYLE_TEMPLATE = """
QMainWindow {{
    background-color: #0f1118;
    color: #f4f6fb;
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 11pt;
}}

QFrame#panelCard {{
    background-color: {surface};
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.04);
}}
QFrame#scanProgress, QFrame#folderCard {{
    background-color: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    padding: 12px;
}}

QToolBox::tab {{
    background-color: #141823;
    border: none;
    border-radius: 10px;
    padding: 10px 14px;
    margin: 2px 12px 4px 12px;
    font-weight: 600;
}}
QToolBox::tab:selected {{
    background-color: rgba(94, 129, 255, 0.25);
}}
QToolBox::tab:hover {{
    background-color: rgba(94, 129, 255, 0.35);
}}

QPushButton {{
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px 16px;
    color: #f4f6fb;
}}
QPushButton:hover {{
    background-color: rgba(255, 255, 255, 0.08);
}}
QPushButton:disabled {{
    color: rgba(255, 255, 255, 0.35);
    background-color: rgba(255, 255, 255, 0.02);
    border-color: rgba(255, 255, 255, 0.04);
}}
QPushButton[class~="accent"] {{
    background-color: {accent};
    border-color: rgba(94, 129, 255, 0.6);
    color: #0a0c12;
    font-weight: 600;
}}
QPushButton[class~="accent"]:hover {{
    background-color: {accent_hover};
}}

QLineEdit, QComboBox, QSpinBox {{
    background-color: rgba(10, 12, 18, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 6px 10px;
    color: #f4f6fb;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {accent};
}}
QComboBox QAbstractItemView {{
    background-color: #141823;
    selection-background-color: {accent};
}}

QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.35);
    background-color: rgba(255, 255, 255, 0.04);
}}
QCheckBox::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}

QProgressBar {{
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    background-color: rgba(255, 255, 255, 0.04);
    text-align: center;
    color: #e9ecf6;
}}
QProgressBar::chunk {{
    border-radius: 8px;
    background-color: {accent};
}}

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea#tiersScroll QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 6px 2px 6px 0;
    border-radius: 4px;
}}
QScrollArea#tiersScroll QScrollBar::handle:vertical {{
    background: rgba(244, 246, 251, 0.35);
    border-radius: 4px;
    min-height: 32px;
}}
QScrollArea#tiersScroll QScrollBar::handle:vertical:hover {{
    background: rgba(244, 246, 251, 0.55);
}}
QScrollArea#tiersScroll QScrollBar::add-line:vertical,
QScrollArea#tiersScroll QScrollBar::sub-line:vertical,
QScrollArea#tiersScroll QScrollBar::up-arrow:vertical,
QScrollArea#tiersScroll QScrollBar::down-arrow:vertical {{
    height: 0;
    width: 0;
    margin: 0;
    border: none;
}}
QScrollArea#tiersScroll QScrollBar::add-page:vertical,
QScrollArea#tiersScroll QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QToolButton#tierToggle {{
    border: none;
    color: #f4f6fb;
    padding: 4px;
    border-radius: 8px;
}}
QToolButton#tierToggle:hover {{
    background-color: rgba(0, 0, 0, 0.1);
}}
QToolButton#cancelButton {{
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 6px 14px;
    color: #f4f6fb;
}}
QToolButton#cancelButton:hover {{
    background-color: rgba(255, 255, 255, 0.08);
}}
QToolButton#cancelButton:disabled {{
    color: rgba(255, 255, 255, 0.35);
    border-color: rgba(255, 255, 255, 0.05);
}}

QLabel#sectionTitle {{
    font-size: 12pt;
    font-weight: 600;
    letter-spacing: 0.4px;
}}
"""

LIBRARY_LIST_STYLE = """
QListWidget {{
    border: 1px solid rgba(255, 255, 255, 0.05);
    padding: 4px;
    background-color: rgba(9, 12, 18, 0.85);
    color: #f0f3ff;
    border-radius: 10px;
}}
QListWidget::item {{
    padding: 4px 8px;
    border-radius: 6px;
}}
QListWidget::item:hover {{
    background-color: rgba(255, 255, 255, 0.05);
}}
QListWidget::item:selected {{
    background-color: rgba(94, 129, 255, 0.55);
    color: #0a0c12;
}}
"""

TIER_LIST_STYLE = """
QListWidget#tierList {{
    border: none;
    padding: 6px 0;
    background-color: transparent;
    color: #f5f7ff;
}}
QListWidget#tierList::item {{
    padding: 6px 12px;
    margin: 1px 4px;
    border-radius: 6px;
}}
QListWidget#tierList::item:alternate {{
    background-color: rgba(255, 255, 255, 0.04);
}}
QListWidget#tierList::item:selected {{
    background-color: rgba(94, 129, 255, 0.55);
    color: #0a0c12;
}}
"""

TIER_CARD_STYLE = """
QFrame#tierCard {{
    background-color: {surface_elevated};
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);
}}
QFrame#tierCard:hover {{
    border-color: rgba(94, 129, 255, 0.45);
}}
QWidget#tierHeader {{
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
}}
QLabel#tierTitle {{
    font-weight: 600;
    color: #f8f9ff;
}}
""".format(
    accent=ACCENT_COLOR,
    accent_hover=ACCENT_COLOR_HOVER,
    surface=SURFACE_COLOR,
    surface_elevated=SURFACE_ELEVATED,
)

TIER_HEADER_COLORS = [
    "#ff6b35",
    "#f7b801",
    "#6a994e",
    "#386fa4",
    "#a267ac",
    "#ef476f",
]


class InfoBar(QFrame):
    """Lightweight inline notice that auto-hides after a delay."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("infoBar")
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)
        self.icon_label = QLabel("ℹ️")
        self.icon_label.setObjectName("infoBarIcon")
        layout.addWidget(self.icon_label)
        self.message_label = QLabel()
        self.message_label.setObjectName("infoBarLabel")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, text: str, duration_ms: int = 3500) -> None:
        """Display *text* for `duration_ms`, hiding automatically."""

        if not text:
            self._timer.stop()
            self.hide()
            return
        self.message_label.setText(text)
        self.show()
        if duration_ms > 0:
            self._timer.start(duration_ms)
        else:
            self._timer.stop()


class ScanCard(QFrame):
    """Unified progress card that represents the scan workflow."""

    cancelRequested = Signal()
    hideRequested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("scanProgress")
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.StrongFocus)
        self._state = SCAN_IDLE
        self._collapsed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.notice = InfoBar(self)
        layout.addWidget(self.notice)

        self.lbl_phase = QLabel("Ready to scan")
        phase_font = self.lbl_phase.font()
        phase_font.setBold(True)
        phase_font.setPointSize(max(8, phase_font.pointSize() - 1))
        self.lbl_phase.setFont(phase_font)
        self.lbl_phase.setStyleSheet(f"color: {SCAN_PHASE_HEADER_COLOR};")

        phase_block = QVBoxLayout()
        phase_block.setContentsMargins(0, 0, 0, 0)
        phase_block.setSpacing(6)
        phase_block.addWidget(self.lbl_phase)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        phase_block.addWidget(self.progress)

        layout.addLayout(phase_block)

        self._progress_color = QColor(SCAN_PHASE1_COLOR)
        self._base_progress_style = (
            "QProgressBar {"
            " border: 1px solid rgba(255, 255, 255, 0.08);"
            " border-radius: 8px;"
            " background-color: rgba(255, 255, 255, 0.04);"
            " text-align: center;"
            " color: #e9ecf6;"
            "}"
            "QProgressBar::chunk {"
            " border-radius: 8px;"
            " background-color: %s;"
            "}"
        )
        self._color_anim = QVariantAnimation(self)
        self._color_anim.setDuration(SCAN_COLOR_ANIM_DURATION_MS)
        self._color_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._color_anim.valueChanged.connect(self._apply_progress_color)
        self._apply_progress_color(self._progress_color)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        actions.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        actions.addStretch(1)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.cancelRequested.emit)
        actions.addWidget(self.btn_cancel)
        self.btn_hide = QPushButton("Hide")
        self.btn_hide.setFlat(True)
        self.btn_hide.setCursor(Qt.PointingHandCursor)
        self.btn_hide.clicked.connect(self.hideRequested.emit)
        actions.addWidget(self.btn_hide)
        layout.addLayout(actions)

        self.set_cancel_visible(False)
        self.set_hide_visible(False)
        self.set_cancel_enabled(False)
        self.notice.hide()

    def set_state(self, state: str) -> None:
        self._state = state

    def state(self) -> str:
        return self._state

    def set_phase_text(self, text: str) -> None:
        self.lbl_phase.setText(text)

    def set_progress_range(self, minimum: int, maximum: int) -> None:
        self.progress.setRange(minimum, maximum)

    def set_progress_value(self, value: int) -> None:
        self.progress.setValue(value)

    def set_progress_text(self, text: str) -> None:
        if text:
            self.progress.setFormat(text)
            self.progress.setTextVisible(True)
        else:
            self.progress.setFormat("")
            self.progress.setTextVisible(False)

    def set_progress_color(self, color: QColor, *, animate: bool = False) -> None:
        target = QColor(color)
        if not target.isValid():
            return
        if animate:
            if self._color_anim.state() == QVariantAnimation.Running:
                self._color_anim.stop()
            self._color_anim.setStartValue(self._progress_color)
            self._color_anim.setEndValue(target)
            self._color_anim.start()
        else:
            if self._color_anim.state() == QVariantAnimation.Running:
                self._color_anim.stop()
            self._apply_progress_color(target)

    def set_cancel_visible(self, visible: bool) -> None:
        self.btn_cancel.setVisible(visible)

    def set_hide_visible(self, visible: bool) -> None:
        self.btn_hide.setVisible(visible)

    def set_cancel_enabled(self, enabled: bool) -> None:
        self.btn_cancel.setEnabled(enabled)

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.setVisible(not collapsed)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def show_notice(self, text: str, duration_ms: int = 3500) -> None:
        self.notice.show_message(text, duration_ms)

    def clear_notice(self) -> None:
        self.notice.show_message("", 0)

    def focus_cancel(self) -> None:
        if self.btn_cancel.isVisible():
            self.btn_cancel.setFocus(Qt.ShortcutFocusReason)

    def _apply_progress_color(self, color: QColor) -> None:
        if not isinstance(color, QColor):
            color = QColor(color)
        if not color.isValid():
            return
        self._progress_color = color
        rgba = f"rgba({color.red()}, {color.green()}, {color.blue()}, 255)"
        self.progress.setStyleSheet(self._base_progress_style % rgba)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key_Escape and self._state in {SCAN_PHASE1, SCAN_PHASE2}:
            if self.btn_cancel.isVisible() and self.btn_cancel.isEnabled():
                self.btn_cancel.setFocus(Qt.ShortcutFocusReason)
            event.accept()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space) and self._state in {SCAN_COMPLETE, SCAN_CANCELLED}:
            self.hideRequested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


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
        self.setStyleSheet(
            APP_STYLE_TEMPLATE.format(
                accent=ACCENT_COLOR,
                accent_hover=ACCENT_COLOR_HOVER,
                surface=SURFACE_COLOR,
            )
        )

        self.settings = QSettings("CHCareer", "Builder")

        saved_root = self.settings.value("root_folder", None, type=str)
        self.root_folder: Optional[str] = saved_root if saved_root and os.path.isdir(saved_root) else None
        if saved_root and not self.root_folder:
            self.settings.remove("root_folder")

        self.library: List[Song] = []
        self._songs_by_path: Dict[str, Song] = {}
        self._nps_jobs_total = 0
        self.tiers_widgets: List[TierList] = []
        self.tier_wrappers: List[QWidget] = []
        self._tier_bodies: List[QWidget] = []
        self._tier_toggles: List[QToolButton] = []
        self._list_delegates: List[CompactItemDelegate] = []
        self.current_tier_names: List[str] = []
        self._procedural_seed = None
        self._scan_active = False
        self.scan_state = SCAN_IDLE
        self._scan_cancel_requested = False
        self._current_scan_message = ""
        self._last_scan_song_count = 0
        stored_collapsed = self.settings.value("scan_card_collapsed", True, type=bool)
        self._scan_card_user_collapsed = bool(stored_collapsed)

        self.btn_pick = QPushButton("Pick Songs Folder…")
        self.btn_scan = QPushButton("Scan Library")
        self.btn_auto = QPushButton("Auto-Arrange")
        self.btn_export = QPushButton("Export Setlist…")
        self.btn_clear_cache = QPushButton("Clear Cache")
        self.btn_clear_cache.setToolTip("Deletes the songs cache so the library will be rebuilt on next scan.")
        for accent_btn in (self.btn_scan, self.btn_auto, self.btn_export):
            accent_btn.setProperty("class", "accent")
            accent_btn.setCursor(Qt.PointingHandCursor)
            accent_btn.setMinimumWidth(accent_btn.sizeHint().width())
        self.btn_clear_cache.setCursor(Qt.PointingHandCursor)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search title / artist / charter…")
        self.search_box.setClearButtonEnabled(True)
        search_icon = self.style().standardIcon(QStyle.SP_FileDialogDetailedView)
        self.search_box.addAction(search_icon, QLineEdit.LeadingPosition)

        self.sort_mode_combo = QComboBox()
        self.sort_mode_combo.addItem("Recommended", "recommended")
        self.sort_mode_combo.addItem("Difficulty (High→Low)", "difficulty_desc")
        self.sort_mode_combo.addItem("Artist (A→Z)", "artist")
        self.sort_mode_combo.addItem("Song Title (A→Z)", "title")

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
        self.chk_weight_nps = QCheckBox("Weight difficulty by NPS")
        self.chk_weight_nps.setChecked(weight_by_nps_setting)
        self._default_weight_nps_tooltip = "Adds Avg/Peak NPS to the difficulty score when enabled."
        self.chk_weight_nps.setToolTip(self._default_weight_nps_tooltip)

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
        stored_tier_count = self.settings.value("tier_count", 9)
        try:
            stored_tier_count = int(stored_tier_count)
        except (TypeError, ValueError):
            stored_tier_count = 9
        clamped_tier_count = max(1, min(20, stored_tier_count))
        self.spin_tiers.setValue(clamped_tier_count)
        self.settings.setValue("tier_count", clamped_tier_count)
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
        self.tiers_layout.setContentsMargins(
            TIER_GRID_LAYOUT_MARGIN,
            TIER_GRID_LAYOUT_MARGIN,
            TIER_GRID_LAYOUT_MARGIN,
            TIER_GRID_LAYOUT_MARGIN,
        )
        self.tiers_layout.setHorizontalSpacing(TIER_COLUMN_SPACING)
        self.tiers_layout.setVerticalSpacing(TIER_COLUMN_SPACING)
        self.tiers_layout.setAlignment(Qt.AlignTop)
        for column in range(TIER_COLUMNS):
            self.tiers_layout.setColumnStretch(column, 1)
            self.tiers_layout.setColumnMinimumWidth(column, TIER_COLUMN_MIN_WIDTH)

        self.tiers_scroll = QScrollArea()
        self.tiers_scroll.setObjectName("tiersScroll")
        self.tiers_scroll.setWidgetResizable(True)
        self.tiers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tiers_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tiers_scroll.setWidget(self.tiers_container)

        self.tiers_vbar = QScrollBar(Qt.Vertical)
        self.tiers_vbar.setObjectName("tiersExternalScrollBar")
        self.tiers_vbar.setFixedWidth(EXTERNAL_VBAR_WIDTH)
        self.tiers_vbar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.tiers_vbar.setFocusPolicy(Qt.NoFocus)
        self.tiers_vbar.hide()
        self.tiers_vbar.setStyleSheet(
            (
                f"QScrollBar:vertical {{\n"
                f"    background: transparent;\n"
                f"    width: {EXTERNAL_VBAR_WIDTH}px;\n"
                f"    margin: 0;\n"
                f"    border: none;\n"
                f"}}\n"
                f"QScrollBar::handle:vertical {{\n"
                f"    background-color: rgba(255, 255, 255, 0.28);\n"
                f"    border-radius: {EXTERNAL_VBAR_WIDTH // 2}px;\n"
                f"    min-height: 36px;\n"
                f"}}\n"
                f"QScrollBar::handle:vertical:hover {{\n"
                f"    background-color: {ACCENT_COLOR};\n"
                f"}}\n"
                "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {\n"
                "    background: transparent;\n"
                "    height: 0px;\n"
                "}\n"
                "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {\n"
                "    background: transparent;\n"
                "}\n"
            )
        )

        tiers_scroll_gutter = QWidget()
        tiers_scroll_gutter.setFixedWidth(TIER_SCROLL_GUTTER_WIDTH)
        tiers_scroll_gutter.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        tiers_wrap_layout = QHBoxLayout()
        tiers_wrap_layout.setContentsMargins(0, 0, 0, 0)
        tiers_wrap_layout.setSpacing(0)
        tiers_wrap_layout.addWidget(self.tiers_scroll, 1)
        tiers_wrap_layout.addWidget(tiers_scroll_gutter)
        tiers_wrap_layout.addWidget(self.tiers_vbar)

        self.tiers_wrap = QWidget()
        self.tiers_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tiers_wrap.setLayout(tiers_wrap_layout)

        self._regenerate_tier_names(procedural_refresh=True)
        self._rebuild_tier_widgets()

        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QHBoxLayout(central)
        self.main_layout.setContentsMargins(
            MAIN_LAYOUT_MARGIN, MAIN_LAYOUT_MARGIN, MAIN_LAYOUT_MARGIN, MAIN_LAYOUT_MARGIN
        )
        self.main_layout.setSpacing(MAIN_LAYOUT_SPACING)
        self.main_layout.setSizeConstraint(QLayout.SetMinimumSize)

        library_card = QFrame()
        library_card.setObjectName("panelCard")
        library_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.library_card = library_card
        library_layout = QVBoxLayout(library_card)
        library_layout.setContentsMargins(
            CARD_CONTENT_MARGIN,
            CARD_CONTENT_MARGIN,
            CARD_CONTENT_MARGIN,
            CARD_CONTENT_MARGIN,
        )
        library_layout.setSpacing(14)
        library_title = QLabel("Library")
        library_title.setObjectName("sectionTitle")
        library_layout.addWidget(library_title)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_row.addWidget(self.search_box, 1)
        search_toolbar = QWidget()
        search_toolbar.setObjectName("libraryToolbar")
        search_toolbar.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        toolbar_layout = QHBoxLayout(search_toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)
        sort_label = QLabel("Sort by:")
        toolbar_layout.addWidget(sort_label)
        toolbar_layout.addWidget(self.sort_mode_combo, 1)
        toolbar_layout.addStretch(1)
        search_row.addWidget(search_toolbar, 1)
        library_layout.addLayout(search_row)

        library_layout.addWidget(self.lib_list, 1)
        self.library_count_label = QLabel("No songs loaded")
        self.library_count_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        library_layout.addWidget(self.library_count_label)
        tip_label = QLabel("Tip: drag songs into tiers; double-click to remove from a tier")
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("color: rgba(244, 246, 251, 0.6);")
        library_layout.addWidget(tip_label)

        tiers_card = QFrame()
        tiers_card.setObjectName("panelCard")
        tiers_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tiers_card = tiers_card
        tiers_card_layout = QVBoxLayout(tiers_card)
        tiers_card_layout.setContentsMargins(
            CARD_CONTENT_MARGIN,
            CARD_CONTENT_MARGIN,
            CARD_CONTENT_MARGIN,
            CARD_CONTENT_MARGIN,
        )
        tiers_card_layout.setSpacing(12)
        tiers_title = QLabel("Tier Builder")
        tiers_title.setObjectName("sectionTitle")
        tiers_card_layout.addWidget(tiers_title)
        tiers_card_layout.addWidget(self.tiers_wrap, 1)

        self.settings_box = QFrame()
        self.settings_box.setObjectName("panelCard")
        self.settings_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        settings_layout = QVBoxLayout(self.settings_box)
        settings_layout.setContentsMargins(18, 18, 18, 18)
        settings_layout.setSpacing(14)
        self.settings_layout = settings_layout

        workflow_title = QLabel("Workflow")
        workflow_title.setObjectName("sectionTitle")
        settings_layout.addWidget(workflow_title)

        folder_card = QFrame()
        folder_card.setObjectName("folderCard")
        folder_layout = QVBoxLayout(folder_card)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)
        folder_header = QHBoxLayout()
        folder_header.setContentsMargins(0, 0, 0, 0)
        folder_header.setSpacing(8)
        folder_header.addWidget(self.btn_pick)
        folder_header.addStretch(1)
        folder_layout.addLayout(folder_header)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(6)
        status_row.addWidget(self.folder_status_indicator)
        status_row.addWidget(self.folder_status_label, 1)
        folder_layout.addLayout(status_row)
        settings_layout.addWidget(folder_card)

        primary_actions = QHBoxLayout()
        primary_actions.setContentsMargins(0, 0, 0, 0)
        primary_actions.setSpacing(10)
        primary_actions.setSizeConstraint(QLayout.SetMinimumSize)
        primary_actions.addWidget(self.btn_scan)
        primary_actions.addWidget(self.btn_auto)
        primary_actions.addWidget(self.btn_export)
        self.primary_actions_layout = primary_actions
        settings_layout.addLayout(primary_actions)

        self._refresh_workflow_button_minimums()

        self.scan_card = ScanCard()
        settings_layout.addWidget(self.scan_card)
        self._set_scan_state(SCAN_IDLE)

        self.settings_toolbox = QToolBox()

        filters_page = QWidget()
        filters_form = QFormLayout(filters_page)
        filters_form.setContentsMargins(12, 12, 12, 12)
        filters_form.setSpacing(10)
        filters_form.addRow("Minimum difficulty:", self.spin_min_diff)
        filters_form.addRow(self.chk_exclude_meme)
        filters_form.addRow(self.chk_group_genre)
        filters_form.addRow(self.chk_artist_career_mode)

        rules_page = QWidget()
        rules_form = QFormLayout(rules_page)
        rules_form.setContentsMargins(12, 12, 12, 12)
        rules_form.setSpacing(10)
        rules_form.addRow(self.chk_longrule)
        self.lbl_artist_limit = QLabel("Max tracks by artist per tier:")
        rules_form.addRow(self.lbl_artist_limit, self.spin_artist_limit)
        rules_form.addRow(self.chk_lower_official)

        advanced_page = QWidget()
        advanced_form = QFormLayout(advanced_page)
        advanced_form.setContentsMargins(12, 12, 12, 12)
        advanced_form.setSpacing(10)
        advanced_form.addRow("Tiers:", self.spin_tiers)
        advanced_form.addRow("Songs per tier:", self.spin_songs_per)
        advanced_form.addRow("Theme:", self.theme_combo)
        advanced_form.addRow(self.chk_weight_nps)

        self.settings_toolbox.addItem(filters_page, "Filters")
        self.settings_toolbox.addItem(rules_page, "Rules")
        self.settings_toolbox.addItem(advanced_page, "Advanced")
        settings_layout.addWidget(self.settings_toolbox)

        settings_layout.addStretch(1)
        settings_layout.addWidget(self.btn_clear_cache, 0, Qt.AlignLeft)

        self._apply_shadow(library_card, blur=16, y=1, alpha=80)
        self._apply_shadow(self.settings_box, blur=16, y=1, alpha=80)

        self.main_layout.addWidget(library_card, 2)
        self.main_layout.addWidget(tiers_card, 3)
        self.main_layout.addWidget(self.settings_box, 2)

        self._refresh_workflow_buttons_and_update()
        self._update_folder_status()

        self._scan_button_default_tooltip = (
            self.btn_scan.toolTip() or "Scan your library recursively for eligible songs."
        )
        self._scan_disabled_tooltip = "Please wait for the current scan to finish."
        self.btn_scan.setToolTip(self._scan_button_default_tooltip)

        self.btn_pick.clicked.connect(self.pick_folder)
        self.btn_scan.clicked.connect(self.scan_now)
        self.btn_auto.clicked.connect(self.auto_arrange)
        self.btn_export.clicked.connect(self.export_now)
        self.btn_clear_cache.clicked.connect(self.clear_cache)
        self.scan_card.cancelRequested.connect(self._cancel_scan)
        self.scan_card.hideRequested.connect(self._on_scan_card_hidden)
        self.spin_tiers.valueChanged.connect(self._on_tier_count_changed)
        self.search_box.textChanged.connect(self._refresh_library_view)
        self.sort_mode_combo.currentIndexChanged.connect(self._refresh_library_view)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        self.chk_group_genre.stateChanged.connect(self._on_group_genre_changed)
        self.chk_artist_career_mode.stateChanged.connect(self._on_artist_career_mode_changed)
        self.chk_exclude_meme.stateChanged.connect(self._on_exclude_meme_changed)
        self.chk_lower_official.stateChanged.connect(self._on_lower_official_changed)
        self.chk_weight_nps.stateChanged.connect(self._on_weight_by_nps_changed)
        self.spin_artist_limit.valueChanged.connect(self._on_artist_limit_changed)
        self.spin_min_diff.valueChanged.connect(self._on_min_difficulty_changed)

        self._connect_tier_scrollbars()
        self._apply_artist_mode_state()
        self._sync_external_tier_scrollbar()
        QTimer.singleShot(0, self._sync_all_tier_heights)
        QTimer.singleShot(0, self._refresh_workflow_buttons_and_update)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not getattr(self, "_workflow_minimums_refreshed_on_show", False):
            self._workflow_minimums_refreshed_on_show = True
            self._refresh_workflow_buttons_and_update()

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if (
            key == Qt.Key_Escape
            and self.scan_state in {SCAN_PHASE1, SCAN_PHASE2}
            and hasattr(self, "scan_card")
        ):
            self.scan_card.setFocus(Qt.ShortcutFocusReason)
            self.scan_card.focus_cancel()
            event.accept()
            return
        super().keyPressEvent(event)

    def _lower_official_enabled(self) -> bool:
        """Return whether official Harmonix/Neversoft charts should be adjusted."""
        return self.chk_lower_official.isChecked()

    def _weight_by_nps_enabled(self) -> bool:
        """Return whether difficulty scores should include NPS weighting."""
        return self.chk_weight_nps.isChecked()


    def _set_scan_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable the Scan controls and update tooltips accordingly."""

        tooltip = self._scan_button_default_tooltip if enabled else self._scan_disabled_tooltip
        if hasattr(self, "btn_scan"):
            self.btn_scan.setEnabled(enabled)
            self.btn_scan.setToolTip(tooltip)
        action = getattr(self, "scan_action", None)
        if action is not None:
            action.setEnabled(enabled)
            action.setToolTip(tooltip)


    def _set_scan_card_collapsed(self, collapsed: bool, *, persist: bool) -> None:
        """Collapse or expand the scan card, optionally persisting the choice."""

        if not hasattr(self, "scan_card"):
            return
        if self.scan_card.is_collapsed() == collapsed and not persist:
            return
        self.scan_card.set_collapsed(collapsed)
        if persist:
            self._scan_card_user_collapsed = collapsed
            self.settings.setValue("scan_card_collapsed", collapsed)


    def _on_scan_card_hidden(self) -> None:
        """Handle user requests to hide the scan card after completion."""

        self._set_scan_card_collapsed(True, persist=True)


    def _set_scan_state(self, state: str) -> None:
        """Update the scan card and internal state machine."""

        previous = getattr(self, "scan_state", SCAN_IDLE)
        self.scan_state = state
        if not hasattr(self, "scan_card"):
            return
        self.scan_card.set_state(state)
        if state == SCAN_IDLE:
            self.scan_card.set_phase_text("Ready to scan")
            self.scan_card.set_progress_range(0, 100)
            self.scan_card.set_progress_value(0)
            self.scan_card.set_progress_text("")
            self.scan_card.set_progress_color(SCAN_PHASE1_COLOR, animate=False)
            self.scan_card.set_cancel_visible(False)
            self.scan_card.set_cancel_enabled(False)
            self.scan_card.set_hide_visible(False)
            self.scan_card.clear_notice()
            self._set_scan_card_collapsed(True, persist=False)
            self._current_scan_message = ""
        elif state in {SCAN_PHASE1, SCAN_PHASE2}:
            self.scan_card.set_cancel_visible(True)
            self.scan_card.set_cancel_enabled(not self._scan_cancel_requested)
            self.scan_card.set_hide_visible(False)
            self._set_scan_card_collapsed(False, persist=True)
            if state == SCAN_PHASE1:
                self.scan_card.set_progress_color(SCAN_PHASE1_COLOR, animate=False)
                self._current_scan_message = "Parsing song metadata"
            else:
                animate = previous == SCAN_PHASE1
                self.scan_card.set_progress_color(SCAN_PHASE2_COLOR, animate=animate)
                self._current_scan_message = ""
        else:
            self.scan_card.set_cancel_visible(False)
            self.scan_card.set_cancel_enabled(False)
            self.scan_card.set_hide_visible(True)


    def _set_weight_nps_enabled(self, enabled: bool) -> None:
        """Enable or disable the NPS weighting checkbox with contextual tooltip."""

        if not hasattr(self, "chk_weight_nps"):
            return
        tooltip = self._default_weight_nps_tooltip if enabled else "Available after NPS scan completes"
        self.chk_weight_nps.setEnabled(enabled)
        self.chk_weight_nps.setToolTip(tooltip)

    def _update_scan_progress_value(self, value: int) -> None:
        """Reflect scan progress in the unified scan card."""

        if not hasattr(self, "scan_card"):
            return
        if self._scan_cancel_requested:
            return
        safe_value = max(0, min(100, int(value)))
        if self.scan_state != SCAN_PHASE1:
            self._set_scan_state(SCAN_PHASE1)
            self.scan_card.set_phase_text("Scanning library (1/2)")
            self.scan_card.set_progress_range(0, 100)
        if not self._current_scan_message:
            self._current_scan_message = "Parsing song metadata"
        prefix = self._current_scan_message.rstrip(" —")
        self.scan_card.set_progress_value(safe_value)
        self.scan_card.set_progress_text(f"{prefix} — {safe_value}%")

    def _update_scan_status(self, text: str) -> None:
        """Update the inline scan status label."""

        if not hasattr(self, "scan_card"):
            return
        if self._scan_cancel_requested:
            return
        raw = (text or "").strip()
        if not raw:
            if self.scan_state == SCAN_PHASE2:
                raw = "Computing chart NPS…"
            elif self.scan_state == SCAN_PHASE1:
                raw = "Scanning library"
        if not raw:
            return
        self._current_scan_message = raw
        if self.scan_state == SCAN_PHASE1:
            percent = max(0, min(100, self.scan_card.progress.value()))
            prefix = raw.rstrip(" —")
            self.scan_card.set_progress_text(f"{prefix} — {percent}%")
        elif self.scan_state == SCAN_PHASE2:
            self.scan_card.show_notice(raw, duration_ms=3000)

    def _reset_scan_progress_ui(self, *, message: str = "Ready to scan") -> None:
        """Hide and reset the scan progress widgets."""

        if not hasattr(self, "scan_card"):
            return
        self._current_scan_message = ""
        self._last_scan_song_count = 0
        self._nps_jobs_total = 0
        self._scan_cancel_requested = False
        self._set_scan_state(SCAN_IDLE)
        self.scan_card.clear_notice()

    def _cancel_scan(self) -> None:
        """Allow the user to cancel an in-progress scan."""

        if not getattr(self, "_scan_active", False):
            self._reset_scan_progress_ui(message="Ready to scan")
            return
        self._scan_cancel_requested = True
        worker = getattr(self, "worker", None)
        if worker is not None:
            worker.stop()
        if hasattr(self, "scan_card"):
            self._current_scan_message = "Cancelling scan…"
            self.scan_card.set_progress_text("Cancelling scan…")
            self.scan_card.set_cancel_enabled(False)

    def _decoration_padding(self) -> int:
        """Return the buffer needed so window chrome never hides tier columns."""

        frame_width = self.frameGeometry().width()
        geo_width = self.geometry().width()
        decoration_padding = max(0, frame_width - geo_width)
        return max(40, decoration_padding)

    def _connect_tier_scrollbars(self) -> None:
        """Bridge the hidden tier scroll area with the external gutter scrollbar."""

        if not hasattr(self, "tiers_scroll") or not hasattr(self, "tiers_vbar"):
            return
        if getattr(self, "_tier_scrollbars_connected", False):
            return
        internal = self.tiers_scroll.verticalScrollBar()
        external = self.tiers_vbar
        if internal is None or external is None:
            return

        external.valueChanged.connect(self._on_external_tier_scroll)
        internal.valueChanged.connect(self._on_internal_tier_scroll)
        internal.rangeChanged.connect(lambda *_: self._sync_external_tier_scrollbar())
        internal.actionTriggered.connect(lambda *_: self._sync_external_tier_scrollbar())
        self._tier_scrollbars_connected = True
        self._sync_external_tier_scrollbar()

    def _sync_external_tier_scrollbar(self) -> None:
        """Mirror the internal vertical scrollbar onto the external gutter bar."""

        if not hasattr(self, "tiers_scroll") or not hasattr(self, "tiers_vbar"):
            return
        internal = self.tiers_scroll.verticalScrollBar()
        external = self.tiers_vbar
        if internal is None or external is None:
            return

        needs_scroll = internal.maximum() > internal.minimum()
        external.blockSignals(True)
        external.setRange(internal.minimum(), internal.maximum())
        external.setPageStep(max(1, internal.pageStep()))
        external.setSingleStep(max(1, internal.singleStep()))
        external.setValue(internal.value())
        external.setVisible(needs_scroll)
        external.setEnabled(needs_scroll)
        external.blockSignals(False)
        if not needs_scroll:
            internal.setValue(0)

    def _on_internal_tier_scroll(self, value: int) -> None:
        """Update the external scrollbar when the internal one moves."""

        if not hasattr(self, "tiers_vbar"):
            return
        external = self.tiers_vbar
        if external.value() != value:
            external.setValue(value)

    def _on_external_tier_scroll(self, value: int) -> None:
        """Update the hidden scroll area when the external bar moves."""

        if not hasattr(self, "tiers_scroll"):
            return
        internal = self.tiers_scroll.verticalScrollBar()
        if internal is None:
            return
        if internal.value() != value:
            internal.setValue(value)

    def _apply_shadow(
        self,
        widget: Optional[QWidget],
        *,
        blur: int = 20,
        x: int = 0,
        y: int = 2,
        alpha: int = 110,
    ) -> None:
        """Attach a drop shadow effect to *widget* with the provided styling."""

        if widget is None:
            return
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(max(0, blur))
        effect.setOffset(x, y)
        effect.setColor(QColor(0, 0, 0, max(0, min(255, alpha))))
        widget.setGraphicsEffect(effect)

    def _refresh_workflow_button_minimums(self) -> None:
        """Ensure workflow buttons expose up-to-date minimum widths."""

        for attr in ("btn_scan", "btn_auto", "btn_export"):
            button = getattr(self, attr, None)
            if button is None:
                continue
            hint_width = button.sizeHint().width()
            if hint_width <= 0:
                continue
            if hint_width > button.minimumWidth():
                button.setMinimumWidth(hint_width)

    def _refresh_workflow_buttons_and_update(self) -> None:
        """Refresh workflow button minimums and immediately enforce constraints."""

        self._refresh_workflow_button_minimums()
        self._update_size_constraints()

    def _workflow_actions_minimum_width(self) -> int:
        """Return the minimum width required to keep workflow buttons on one row."""

        buttons = []
        for attr in ("btn_scan", "btn_auto", "btn_export"):
            button = getattr(self, attr, None)
            if button is None:
                continue
            hint_width = button.sizeHint().width()
            width = max(button.minimumWidth(), hint_width)
            buttons.append(width)
        spacing_total = 0
        actions_margins = 0
        if hasattr(self, "primary_actions_layout") and buttons:
            spacing = self.primary_actions_layout.spacing()
            spacing_total = spacing * max(0, len(buttons) - 1)
            primary_margins: QMargins = self.primary_actions_layout.contentsMargins()
            actions_margins = primary_margins.left() + primary_margins.right()
        settings_margins = 0
        layout = getattr(self, "settings_layout", None)
        if layout is not None:
            margins: QMargins = layout.contentsMargins()
            settings_margins = margins.left() + margins.right()
        buffer = 6 if buttons else 0
        return sum(buttons) + spacing_total + actions_margins + settings_margins + buffer

    def _update_size_constraints(self) -> None:
        """Enforce minimum widget sizes so the layout remains usable."""
        width_before_adjust = self.width()
        actions_min_width = self._workflow_actions_minimum_width()
        settings_min = max(SETTINGS_MIN_WIDTH, actions_min_width)
        window_min_width = (
            LIBRARY_PANEL_MIN_WIDTH
            + settings_min
            + TIERS_PANEL_MIN_WIDTH
            + 2 * MAIN_LAYOUT_SPACING
            + 2 * MAIN_LAYOUT_MARGIN
        )
        if hasattr(self, 'lib_list'):
            self.lib_list.setMinimumWidth(LIBRARY_MIN_WIDTH)
        if hasattr(self, 'library_card'):
            self.library_card.setMinimumWidth(LIBRARY_PANEL_MIN_WIDTH)
        if hasattr(self, 'settings_box'):
            self.settings_box.setMinimumWidth(settings_min)
        if hasattr(self, 'tiers_scroll'):
            tiers_content_min_width = (
                TIER_COLUMNS * TIER_COLUMN_MIN_WIDTH + (TIER_COLUMNS - 1) * TIER_COLUMN_SPACING
            )
            self.tiers_scroll.setMinimumWidth(tiers_content_min_width)
            if hasattr(self, 'tiers_wrap'):
                tiers_wrap_min_width = (
                    tiers_content_min_width + TIER_SCROLL_GUTTER_WIDTH + EXTERNAL_VBAR_WIDTH
                )
                self.tiers_wrap.setMinimumWidth(tiers_wrap_min_width)
        if hasattr(self, 'tiers_card'):
            self.tiers_card.setMinimumWidth(TIERS_PANEL_MIN_WIDTH)
        if width_before_adjust < window_min_width:
            safe_width = window_min_width + self._decoration_padding()
            self.resize(safe_width, self.height())
        if hasattr(self, 'main_layout'):
            self.setMinimumSize(window_min_width, WINDOW_MIN_HEIGHT)
            target_width = max(self.width(), window_min_width)
            target_height = max(self.height(), WINDOW_MIN_HEIGHT)
            if target_width != self.width() or target_height != self.height():
                self.resize(target_width, target_height)
        if hasattr(self, 'tiers_scroll'):
            allow_horizontal_scroll = width_before_adjust < window_min_width
            policy = Qt.ScrollBarAsNeeded if allow_horizontal_scroll else Qt.ScrollBarAlwaysOff
            self.tiers_scroll.setHorizontalScrollBarPolicy(policy)
        self._sync_external_tier_scrollbar()

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
        self.settings.setValue("tier_count", value)
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
        self._tier_bodies.clear()
        self._tier_toggles.clear()

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
            self._sync_tier_height(tier)

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
            self.tiers_layout.setColumnMinimumWidth(col, TIER_COLUMN_MIN_WIDTH)

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
        panel.setMinimumWidth(TIER_COLUMN_MIN_WIDTH)
        panel.setStyleSheet(TIER_CARD_STYLE)

        self._apply_shadow(panel, blur=20, y=2, alpha=100)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("tierHeader")
        header_color = TIER_HEADER_COLORS[index % len(TIER_HEADER_COLORS)]
        header.setStyleSheet(
            f"background-color: {header_color}; border-top-left-radius: 14px; border-top-right-radius: 14px;"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(10)

        icon_label = QLabel()
        icon = self.style().standardIcon(QStyle.SP_MediaPlay)
        icon_label.setPixmap(icon.pixmap(20, 20))
        header_layout.addWidget(icon_label)

        title = QLabel(tier.title)
        title.setObjectName("tierTitle")
        title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        header_layout.addWidget(title, 1)

        toggle = QToolButton()
        toggle.setObjectName("tierToggle")
        toggle.setCheckable(True)
        toggle.setChecked(True)
        toggle.setArrowType(Qt.DownArrow)
        toggle.setToolButtonStyle(Qt.ToolButtonIconOnly)
        toggle.setCursor(Qt.PointingHandCursor)
        header_layout.addWidget(toggle)

        layout.addWidget(header)
        tier.title_label = title

        body = QWidget()
        body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(6)

        tier.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tier.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tier.setViewportMargins(0, 0, 6, 0)
        body_layout.addWidget(tier)
        layout.addWidget(body)

        toggle.toggled.connect(lambda checked, t=tier, b=body, btn=toggle: self._on_tier_toggle(t, b, btn, checked))
        self._tier_bodies.append(body)
        self._tier_toggles.append(toggle)
        return panel

    def _on_tier_toggle(self, tier: TierList, body: QWidget, toggle: QToolButton, checked: bool) -> None:
        """Handle expanding/collapsing of tier panels while keeping layout tidy."""

        toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        body.setVisible(checked)
        tier.setVisible(checked)
        if checked:
            self._sync_tier_height(tier)
        else:
            tier.setFixedHeight(0)
            body.setFixedHeight(0)
        self._sync_all_tier_heights()

    def _sync_tier_height(self, tier: TierList) -> None:
        """Resize a tier to show the configured number of rows."""
        if not tier.isVisible() and tier.parentWidget() is not None:
            return
        configured_rows = self.spin_songs_per.value()
        target_rows = max(configured_rows, tier.count())
        height = self._tier_height_for(tier, target_rows)
        if tier.count() == 0:
            cap_height = self._tier_height_for(tier, configured_rows)
            height = min(height, cap_height)
        tier.setFixedHeight(height)
        parent = tier.parentWidget()
        if parent:
            layout = parent.layout()
            margins = layout.contentsMargins() if layout is not None else QMargins()
            total_height = height + margins.top() + margins.bottom()
            parent.setFixedHeight(total_height)
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
        if hasattr(self, "tiers_scroll") and hasattr(self, "tiers_container"):
            viewport_height = self.tiers_scroll.viewport().height()
            content_height = self.tiers_container.sizeHint().height()
            if viewport_height > 0 and content_height <= viewport_height:
                self.tiers_scroll.verticalScrollBar().setValue(0)
        self._sync_external_tier_scrollbar()

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

        sort_mode = getattr(self, "sort_mode_combo", None)
        sort_key = sort_mode.currentData() if sort_mode is not None else "recommended"

        if sort_key == "difficulty_desc":
            filtered.sort(
                key=lambda song: (
                    effective_score(song, lower_official, weight_by_nps=weight_by_nps),
                    (song.name or "").lower(),
                ),
                reverse=True,
            )
        elif sort_key == "artist":
            filtered.sort(
                key=lambda song: (
                    strip_color_tags(song.artist or "").lower(),
                    (song.name or "").lower(),
                )
            )
        elif sort_key == "title":
            filtered.sort(
                key=lambda song: (
                    strip_color_tags(song.name or "").lower(),
                    strip_color_tags(song.artist or "").lower(),
                )
            )
        else:
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
        self._update_library_summary()

    def _update_library_summary(self) -> None:
        """Refresh the library footer summary with the current counts."""

        if not hasattr(self, "library_count_label"):
            return
        total = len(self.library)
        visible = self.lib_list.count()
        if total and visible != total:
            text = f"Showing {visible} of {total} songs"
        elif visible:
            text = f"{visible} songs"
        else:
            text = "No songs loaded"
        self.library_count_label.setText(text)

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

    def _on_nps_progress(self, completed: int, total: int) -> None:
        """Update the scan card while NPS jobs execute."""

        if not hasattr(self, "scan_card"):
            return
        if self._scan_cancel_requested:
            return
        safe_total = max(0, total)
        safe_completed = max(0, min(completed, safe_total if safe_total else completed))
        self._nps_jobs_total = safe_total
        if safe_total <= 0:
            return
        if self.scan_state != SCAN_PHASE2:
            self._set_scan_state(SCAN_PHASE2)
        self.scan_card.set_phase_text("Computing chart NPS (2/2)")
        self.scan_card.set_progress_range(0, safe_total)
        self.scan_card.set_progress_value(safe_completed)
        progress_text = f"{safe_completed} / {safe_total} songs analyzed"
        self.scan_card.set_progress_text(progress_text)
        self._current_scan_message = progress_text

    def _on_nps_update(self, song_path: str, avg: float, peak: float) -> None:
        """Store freshly computed NPS values for a song."""

        song = self._songs_by_path.get(song_path)
        if not song:
            return
        song.nps_avg = avg or 0.0
        song.nps_peak = peak or 0.0

    def _on_nps_done(self) -> None:
        """Handle completion (or cancellation) of the background NPS scan."""

        self._scan_active = False
        self._set_scan_controls_enabled(True)
        self._set_weight_nps_enabled(True)
        if not hasattr(self, "scan_card"):
            self._scan_cancel_requested = False
            return
        if self._scan_cancel_requested:
            self._set_scan_state(SCAN_CANCELLED)
            self.scan_card.set_phase_text("Scan cancelled")
            self.scan_card.set_progress_range(0, 100)
            self.scan_card.set_progress_value(0)
            self.scan_card.set_progress_text("Scan cancelled")
            self.scan_card.clear_notice()
            self._scan_cancel_requested = False
            return
        self._set_scan_state(SCAN_COMPLETE)
        self.scan_card.set_phase_text("Scan complete")
        detail = f"Found {self._last_scan_song_count} eligible songs."
        self._current_scan_message = detail
        if self._nps_jobs_total > 0:
            total = max(1, self._nps_jobs_total)
            self.scan_card.set_progress_range(0, total)
            self.scan_card.set_progress_value(total)
        else:
            self.scan_card.set_progress_range(0, 100)
            self.scan_card.set_progress_value(100)
        self.scan_card.set_progress_text(detail)
        self.scan_card.clear_notice()
        self._scan_cancel_requested = False
        self._refresh_library_view()
        self._refresh_tier_tooltips()
        self._refresh_library_view()
        self._refresh_tier_tooltips()

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
        if self._scan_active:
            QMessageBox.information(
                self,
                "Scan in progress",
                "Scan already in progress. Please wait for the current scan to finish.",
            )
            return
        if not self.root_folder or not os.path.isdir(self.root_folder):
            self.root_folder = None
            self.settings.remove("root_folder")
            self._update_folder_status()
            QMessageBox.warning(self, "No folder", "Please pick your TOP-LEVEL songs folder first.")
            return

        self._scan_active = True
        self._set_scan_controls_enabled(False)
        self._scan_cancel_requested = False
        self._current_scan_message = ""
        self._last_scan_song_count = 0
        self._nps_jobs_total = 0
        self._set_scan_state(SCAN_PHASE1)
        if hasattr(self, "scan_card"):
            self.scan_card.clear_notice()
            self.scan_card.set_phase_text("Scanning library (1/2)")
            self.scan_card.set_progress_range(0, 100)
            self.scan_card.set_progress_value(0)
            self._current_scan_message = "Parsing song metadata"
            self.scan_card.set_progress_text("Parsing song metadata — 0%")

        self.thread = QThread(self)
        cache_db = get_cache_path()
        self.worker = ScanWorker(self.root_folder, cache_db)
        self.worker.moveToThread(self.thread)

        self._songs_by_path = {}
        self._set_weight_nps_enabled(False)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._update_scan_progress_value)
        self.worker.message.connect(self._update_scan_status)
        self.worker.done.connect(self._scan_finished)
        self.worker.nps_progress.connect(self._on_nps_progress)
        self.worker.nps_update.connect(self._on_nps_update)
        self.worker.nps_done.connect(self._on_nps_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        try:
            self.thread.start()
        except Exception:
            self._scan_active = False
            self._set_scan_controls_enabled(True)
            self._set_scan_state(SCAN_ERROR)
            if hasattr(self, "scan_card"):
                self.scan_card.set_phase_text("Scan failed")
                self.scan_card.set_progress_text("Could not start the scan. See logs for details.")
            raise

    def _scan_finished(self, songs: List[Song]) -> None:
        """Handle completion of the background scan and refresh the UI."""
        self.library = songs
        self._songs_by_path = {song.path: song for song in songs}
        self._refresh_library_view()
        self._last_scan_song_count = len(songs)
        if self._scan_cancel_requested:
            return
        if self._nps_jobs_total > 0:
            if self.scan_state != SCAN_PHASE2:
                self._set_scan_state(SCAN_PHASE2)
            if hasattr(self, "scan_card"):
                total = max(1, self._nps_jobs_total)
                self.scan_card.set_phase_text("Computing chart NPS (2/2)")
                self.scan_card.set_progress_range(0, total)
                self.scan_card.set_progress_value(0)
                progress_text = f"0 / {total} songs analyzed"
                self.scan_card.set_progress_text(progress_text)
                self._current_scan_message = progress_text
                self.scan_card.show_notice(
                    f"Found {len(songs)} songs. NPS is computing…",
                    duration_ms=3500,
                )
        else:
            if hasattr(self, "scan_card"):
                self.scan_card.set_progress_range(0, 100)
                self.scan_card.set_progress_value(100)
                detail = f"Found {len(songs)} eligible songs."
                self.scan_card.set_progress_text(detail)
                self._current_scan_message = detail

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


