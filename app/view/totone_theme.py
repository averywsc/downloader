from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtGui import QColor, QFont, QIcon, QPalette

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QWidget


@dataclass(frozen=True)
class TotonePalette:
    name: str
    bg: str
    panel: str
    hover: str
    ink: str
    mute: str
    line: str
    edge: str
    acc: str
    accink: str
    isDark: bool = True


TOTONE_PRESETS: dict[str, TotonePalette] = {
    "Totone Navy": TotonePalette(
        name="Totone Navy",
        bg="#050c1f", panel="#091534", hover="#0c1b42",
        ink="#f4f7ff", mute="#8d9cc4", line="#16254d", edge="#34477e",
        acc="#ffffff", accink="#050c1f", isDark=True,
    ),
    "Midnight OLED": TotonePalette(
        name="Midnight OLED",
        bg="#000000", panel="#0a0c10", hover="#12161d",
        ink="#f5f7fa", mute="#8b949e", line="#1c2128", edge="#30363d",
        acc="#ffffff", accink="#000000", isDark=True,
    ),
    "Cybercore Lime": TotonePalette(
        name="Cybercore Lime",
        bg="#060d09", panel="#0c1a12", hover="#12271b",
        ink="#ebfff2", mute="#7bb894", line="#163322", edge="#28593d",
        acc="#a3ff12", accink="#060d09", isDark=True,
    ),
    "Frutiger Aero": TotonePalette(
        name="Frutiger Aero",
        bg="#061826", panel="#0b253b", hover="#10324f",
        ink="#edf8ff", mute="#83b8d9", line="#133c5e", edge="#266596",
        acc="#38bdf8", accink="#061826", isDark=True,
    ),
    "Sakura Dusk": TotonePalette(
        name="Sakura Dusk",
        bg="#160b16", panel="#221223", hover="#2d172e",
        ink="#fff0f6", mute="#c490ab", line="#381d3a", edge="#613463",
        acc="#ff7eb6", accink="#160b16", isDark=True,
    ),
    "Studio Neutral": TotonePalette(
        name="Studio Neutral",
        bg="#121214", panel="#1c1c20", hover="#25252b",
        ink="#f4f4f5", mute="#9ca3af", line="#2b2b31", edge="#42424d",
        acc="#ffffff", accink="#121214", isDark=True,
    ),
    "Warm Film": TotonePalette(
        name="Warm Film",
        bg="#14100c", panel="#1f1913", hover="#2a221a",
        ink="#fdf6ec", mute="#b8a48c", line="#332920", edge="#574534",
        acc="#f5b942", accink="#14100c", isDark=True,
    ),
    "Paper Light": TotonePalette(
        name="Paper Light",
        bg="#f4f6fb", panel="#ffffff", hover="#ebf0fa",
        ink="#0c1428", mute="#556280", line="#dbe2f0", edge="#b6c3de",
        acc="#050c1f", accink="#ffffff", isDark=False,
    ),
}

TOTONE_THEME_NAMES = list(TOTONE_PRESETS.keys())

# Default Totone Navy constants for direct imports
TOTONE_BG = "#050c1f"
TOTONE_PANEL = "#091534"
TOTONE_INK = "#f4f7ff"
TOTONE_MUTE = "#8d9cc4"
TOTONE_LINE = "#16254d"
TOTONE_EDGE = "#34477e"
TOTONE_ACC = "#ffffff"
TOTONE_ACC_INK = "#050c1f"
TOTONE_DANGER = "#fda4af"

TOTONE_FONT_FAMILIES = ["Archivo", "Segoe UI", "Helvetica Neue", "Arial", "sans-serif"]

_QSS_START = "/* DODOWN_TOTONE_QSS_START */"
_QSS_END = "/* DODOWN_TOTONE_QSS_END */"


def currentPalette(presetName: str | None = None) -> TotonePalette:
    if presetName is None:
        try:
            from app.config.cfg import cfg
            presetName = cfg.totoneThemePreset.value
        except Exception:
            presetName = "Totone Navy"
    return TOTONE_PRESETS.get(presetName, TOTONE_PRESETS["Totone Navy"])


def dodownIcon() -> QIcon:
    """Return the Totone-styled Dodown app icon."""
    from app.config.paths import EXECUTABLE_DIR

    svgPath = EXECUTABLE_DIR / "app" / "assets" / "dodown_logo.svg"
    if svgPath.is_file():
        return QIcon(str(svgPath))
    pngPath = EXECUTABLE_DIR / "app" / "assets" / "logo.png"
    if pngPath.is_file():
        return QIcon(str(pngPath))
    return QIcon(":/image/logo.png")


def buildTotoneQss(p: TotonePalette) -> str:
    return f"""{_QSS_START}
/* Dodown — Totone Studio UI Theme ({p.name}) */

QWidget {{
    color: {p.ink};
    font-family: "Archivo", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    selection-background-color: {p.acc};
    selection-color: {p.accink};
}}

MainWindow, MSFluentWindow, OobeWindow {{
    background-color: {p.bg};
}}

QStackedWidget, QStackedWidget > QWidget {{
    background-color: {p.bg};
}}

MSFluentTitleBar, TitleBar, StandardTitleBar {{
    background-color: {p.panel};
    border-bottom: 1px solid {p.line};
}}

MSFluentTitleBar > QLabel,
TitleBar > QLabel,
StandardTitleBar > QLabel,
QLabel#totoneBrandTitle {{
    color: {p.ink};
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -0.4px;
    background: transparent;
}}

NavigationBar, NavigationInterface, NavigationPanel {{
    background-color: {p.panel};
    border-right: 1px solid {p.line};
}}

NavigationBarPushButton, NavigationTreeWidget, NavigationPushButton {{
    color: {p.mute};
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
}}

NavigationBarPushButton:hover, NavigationPushButton:hover {{
    color: {p.ink};
    background-color: {p.line};
    border: 1px solid {p.edge};
}}

NavigationBarPushButton[isSelected=true], NavigationPushButton[isSelected=true] {{
    color: {p.accink};
    background-color: {p.acc};
    border: 1px solid {p.acc};
    font-weight: 700;
}}

QWidget#totoneToolbar {{
    background-color: {p.panel};
    border-bottom: 1px solid {p.line};
}}

QWidget#totoneStatusBar {{
    background-color: {p.panel};
    border-top: 1px solid {p.line};
}}

QLabel#totoneStatusLabel {{
    color: {p.mute};
    font-size: 11.5px;
    background: transparent;
}}

PushButton, ToolButton, ToggleToolButton, DropDownPushButton, DropDownToolButton, SplitPushButton {{
    color: {p.ink};
    background-color: {p.panel};
    border: 1px solid {p.edge};
    border-radius: 3px;
    padding: 5px 11px;
}}

PushButton:hover, ToolButton:hover, ToggleToolButton:hover,
DropDownPushButton:hover, DropDownToolButton:hover {{
    background-color: {p.line};
    border-color: {p.edge};
    color: {p.ink};
}}

PushButton:pressed, ToolButton:pressed, DropDownPushButton:pressed, DropDownToolButton:pressed {{
    background-color: {p.bg};
    border-color: {p.acc};
}}

PushButton:disabled, ToolButton:disabled, ToggleToolButton:disabled {{
    color: {p.mute};
    background-color: {p.bg};
    border-color: {p.line};
}}

ToggleToolButton:checked, TogglePushButton:checked {{
    background-color: {p.acc};
    border-color: {p.acc};
    color: {p.accink};
    font-weight: 700;
}}

PrimaryPushButton, PrimaryToolButton, PrimaryDropDownPushButton, PrimarySplitPushButton {{
    color: {p.accink};
    background-color: {p.acc};
    border: 1px solid {p.acc};
    border-radius: 3px;
    font-weight: 700;
    padding: 5px 12px;
}}

PrimaryPushButton:hover, PrimaryToolButton:hover {{
    opacity: 0.92;
    background-color: {p.acc};
    border-color: {p.ink};
    color: {p.accink};
}}

PrimaryPushButton:disabled, PrimaryToolButton:disabled {{
    background-color: {p.line};
    border-color: {p.line};
    color: {p.mute};
}}

TransparentToolButton, TransparentPushButton, HyperlinkButton {{
    color: {p.ink};
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
}}

TransparentToolButton:hover, TransparentPushButton:hover, HyperlinkButton:hover {{
    background-color: {p.line};
    border-color: {p.edge};
}}

LineEdit, SearchLineEdit, PasswordLineEdit, TextEdit, PlainTextEdit,
ComboBox, EditableComboBox, SpinBox, DoubleSpinBox, QLineEdit, QPlainTextEdit {{
    color: {p.ink};
    background-color: {p.bg};
    border: 1px solid {p.edge};
    border-radius: 3px;
    padding: 4px 8px;
}}

LineEdit:hover, SearchLineEdit:hover, ComboBox:hover, SpinBox:hover, TextEdit:hover, PlainTextEdit:hover {{
    border-color: {p.mute};
}}

LineEdit:focus, SearchLineEdit:focus, ComboBox:focus, SpinBox:focus, TextEdit:focus, PlainTextEdit:focus {{
    border: 1px solid {p.acc};
    background-color: {p.bg};
}}

CardWidget, TaskCard, SettingCard, SimpleCardWidget, HeaderCardWidget, ExpandSettingCard {{
    background-color: {p.panel};
    border: 1px solid {p.line};
    border-radius: 4px;
}}

CardWidget:hover, TaskCard:hover, SettingCard:hover {{
    border: 1px solid {p.edge};
    background-color: {p.hover};
}}

SegmentedWidget, SegmentedToggleToolWidget, Pivot {{
    background-color: {p.panel};
    border: 1px solid {p.line};
    border-radius: 4px;
}}

SegmentedItem, PivotItem {{
    color: {p.mute};
    font-weight: 600;
    border-radius: 3px;
}}

SegmentedItem:hover, PivotItem:hover {{
    color: {p.ink};
}}

SegmentedItem[isSelected=true], PivotItem[isSelected=true] {{
    color: {p.accink};
    background-color: {p.acc};
    font-weight: 700;
}}

CaptionLabel {{
    color: {p.mute};
    background: transparent;
}}

BodyLabel, StrongBodyLabel, SubtitleLabel, TitleLabel, LargeTitleLabel, DisplayLabel {{
    color: {p.ink};
    background: transparent;
}}

ProgressBar, IndeterminateProgressBar {{
    background-color: {p.bg};
    border: 1px solid {p.line};
    border-radius: 3px;
    min-height: 5px;
    max-height: 6px;
}}

RoundMenu, CheckableMenu, CommandBarView, FlyoutView, FlyoutViewBase {{
    background-color: {p.panel};
    border: 1px solid {p.edge};
    border-radius: 5px;
}}

QMenu {{
    background-color: {p.panel};
    border: 1px solid {p.edge};
    border-radius: 5px;
    padding: 4px;
}}

QMenu::item {{
    color: {p.ink};
    padding: 6px 12px;
    border-radius: 3px;
}}

QMenu::item:selected {{
    background-color: {p.line};
}}

QToolTip {{
    background-color: {p.panel};
    color: {p.ink};
    border: 1px solid {p.edge};
    border-radius: 3px;
    padding: 4px 8px;
}}

InfoBar {{
    background-color: {p.panel};
    border: 1px solid {p.edge};
    border-radius: 5px;
}}

QDialog, MessageBox, MessageBoxBase {{
    background-color: {p.panel};
    border: 1px solid {p.edge};
    border-radius: 5px;
}}

QFrame#centerWidget, QWidget#widget {{
    background-color: {p.panel};
    border: 1px solid {p.edge};
    border-radius: 5px;
}}

QScrollArea, ScrollArea, SingleDirectionScrollArea, FastScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: {p.panel};
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {p.edge};
    min-height: 28px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {p.mute};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0;
}}

QScrollBar:horizontal {{
    background: {p.panel};
    height: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: {p.edge};
    min-width: 28px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {p.mute};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
    width: 0;
}}

QTreeView, QListView, QTableView, TreeView, ListView, TableView, QListWidget {{
    background-color: {p.bg};
    alternate-background-color: {p.panel};
    border: 1px solid {p.line};
    border-radius: 4px;
    color: {p.ink};
}}

QTreeView::item:hover, QListView::item:hover, QTableView::item:hover, QListWidget::item:hover {{
    background-color: {p.line};
}}

QTreeView::item:selected, QListView::item:selected, QTableView::item:selected, QListWidget::item:selected {{
    background-color: {p.acc};
    color: {p.accink};
}}
{_QSS_END}"""


def buildTotonePalette(p: TotonePalette | None = None) -> QPalette:
    p = p or currentPalette()
    palette = QPalette()
    bg = QColor(p.bg)
    panel = QColor(p.panel)
    ink = QColor(p.ink)
    mute = QColor(p.mute)
    line = QColor(p.line)
    acc = QColor(p.acc)
    accInk = QColor(p.accink)

    palette.setColor(QPalette.ColorRole.Window, bg)
    palette.setColor(QPalette.ColorRole.WindowText, ink)
    palette.setColor(QPalette.ColorRole.Base, bg)
    palette.setColor(QPalette.ColorRole.AlternateBase, panel)
    palette.setColor(QPalette.ColorRole.ToolTipBase, panel)
    palette.setColor(QPalette.ColorRole.ToolTipText, ink)
    palette.setColor(QPalette.ColorRole.Text, ink)
    palette.setColor(QPalette.ColorRole.PlaceholderText, mute)
    palette.setColor(QPalette.ColorRole.Button, panel)
    palette.setColor(QPalette.ColorRole.ButtonText, ink)
    palette.setColor(QPalette.ColorRole.BrightText, acc)
    palette.setColor(QPalette.ColorRole.Highlight, acc)
    palette.setColor(QPalette.ColorRole.HighlightedText, accInk)
    palette.setColor(QPalette.ColorRole.Link, acc)
    palette.setColor(QPalette.ColorRole.Mid, line)
    palette.setColor(QPalette.ColorRole.Dark, bg)
    palette.setColor(QPalette.ColorRole.Light, QColor(p.edge))

    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, mute)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, mute)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, mute)
    return palette


def applyTotoneTheme(application: QApplication, presetName: str | None = None) -> TotonePalette:
    """Apply the selected Totone Studio theme preset across the entire app."""
    from qfluentwidgets import Theme, setTheme, setThemeColor

    p = currentPalette(presetName)
    setTheme(Theme.DARK if p.isDark else Theme.LIGHT, save=False)
    setThemeColor(QColor(p.acc), save=False)

    application.setPalette(buildTotonePalette(p))

    font = QFont()
    font.setFamilies(TOTONE_FONT_FAMILIES)
    font.setPointSize(10)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    application.setFont(font)

    existing = application.styleSheet() or ""
    if _QSS_START in existing and _QSS_END in existing:
        before = existing.split(_QSS_START, 1)[0]
        after = existing.split(_QSS_END, 1)[1]
        base = (before + after).strip()
    else:
        base = existing.strip()

    application.setStyleSheet((base + "\n" + buildTotoneQss(p)).strip())
    return p


def styleWindowTotone(window: QWidget, presetName: str | None = None) -> None:
    """Apply Totone window-level chrome and background colors."""
    p = currentPalette(presetName)
    if hasattr(window, "setCustomBackgroundColor"):
        window.setCustomBackgroundColor(QColor(p.bg), QColor(p.bg))
    if hasattr(window, "setMicaEffectEnabled"):
        window.setMicaEffectEnabled(False)
    window.setWindowIcon(dodownIcon())
