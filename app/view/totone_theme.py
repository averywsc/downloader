from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QColor, QFont, QIcon, QPalette

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QWidget

# Totone Studio Design Tokens (from totone/css/core.css & studio.css)
TOTONE_BG = "#050c1f"       # --bg: deep midnight navy canvas
TOTONE_PANEL = "#091534"    # --panel: dark navy surfaces, headers, cards, docks
TOTONE_INK = "#f4f7ff"      # --ink: crisp off-white text
TOTONE_MUTE = "#8d9cc4"     # --mute: muted slate-blue secondary text
TOTONE_LINE = "#16254d"     # --line: subtle navy dividers & hover surface
TOTONE_EDGE = "#34477e"     # --edge: crisp 1px navy borders
TOTONE_ACC = "#ffffff"      # --acc: high-contrast pure white accent
TOTONE_ACC_INK = "#050c1f"  # --accink: deep navy text on white accent controls
TOTONE_DANGER = "#fda4af"   # danger / destructive action tint
TOTONE_GOLD = "#fde68a"     # donate / highlight pill text
TOTONE_GOLD_BG = "rgba(245, 158, 11, 0.10)"
TOTONE_GOLD_EDGE = "rgba(245, 158, 11, 0.42)"

TOTONE_FONT_FAMILIES = ["Archivo", "Segoe UI", "Helvetica Neue", "Arial", "sans-serif"]


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


TOTONE_QSS = f"""
/* =====================================================================
   Dodown — Totone Studio UI Theme
   Palette: bg {TOTONE_BG} | panel {TOTONE_PANEL} | ink {TOTONE_INK}
            mute {TOTONE_MUTE} | line {TOTONE_LINE} | edge {TOTONE_EDGE}
            acc {TOTONE_ACC} | accink {TOTONE_ACC_INK}
   ===================================================================== */

QWidget {{
    color: {TOTONE_INK};
    font-family: "Archivo", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    selection-background-color: {TOTONE_ACC};
    selection-color: {TOTONE_ACC_INK};
}}

/* Main window & top-level surfaces */
MainWindow, MSFluentWindow, OobeWindow {{
    background-color: {TOTONE_BG};
}}

QStackedWidget, QStackedWidget > QWidget {{
    background-color: {TOTONE_BG};
}}

/* Totone Single-Row Header / TitleBar */
MSFluentTitleBar, TitleBar, StandardTitleBar {{
    background-color: {TOTONE_PANEL};
    border-bottom: 1px solid {TOTONE_LINE};
}}

MSFluentTitleBar > QLabel,
TitleBar > QLabel,
StandardTitleBar > QLabel,
QLabel#totoneBrandTitle {{
    color: {TOTONE_INK};
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -0.4px;
    background: transparent;
}}

/* Totone Left Quick-Tool Dock / Navigation Rail */
NavigationBar, NavigationInterface, NavigationPanel {{
    background-color: {TOTONE_PANEL};
    border-right: 1px solid {TOTONE_LINE};
}}

NavigationBarPushButton, NavigationTreeWidget, NavigationPushButton {{
    color: {TOTONE_MUTE};
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
}}

NavigationBarPushButton:hover, NavigationPushButton:hover {{
    color: {TOTONE_INK};
    background-color: {TOTONE_LINE};
    border: 1px solid {TOTONE_EDGE};
}}

NavigationBarPushButton[isSelected=true], NavigationPushButton[isSelected=true] {{
    color: {TOTONE_ACC_INK};
    background-color: {TOTONE_ACC};
    border: 1px solid {TOTONE_ACC};
    font-weight: 700;
}}

/* Totone Toolbar & Status Bar */
QWidget#totoneToolbar {{
    background-color: {TOTONE_PANEL};
    border-bottom: 1px solid {TOTONE_LINE};
}}

QWidget#totoneStatusBar {{
    background-color: {TOTONE_PANEL};
    border-top: 1px solid {TOTONE_LINE};
}}

QLabel#totoneStatusLabel {{
    color: {TOTONE_MUTE};
    font-size: 11.5px;
    background: transparent;
}}

/* Totone Buttons — crisp 1px edge border, 3px radius */
PushButton, ToolButton, ToggleToolButton, DropDownPushButton, DropDownToolButton, SplitPushButton {{
    color: {TOTONE_INK};
    background-color: {TOTONE_PANEL};
    border: 1px solid {TOTONE_EDGE};
    border-radius: 3px;
    padding: 5px 11px;
}}

PushButton:hover, ToolButton:hover, ToggleToolButton:hover,
DropDownPushButton:hover, DropDownToolButton:hover {{
    background-color: {TOTONE_LINE};
    border-color: {TOTONE_EDGE};
    color: {TOTONE_INK};
}}

PushButton:pressed, ToolButton:pressed, DropDownPushButton:pressed, DropDownToolButton:pressed {{
    background-color: {TOTONE_BG};
    border-color: {TOTONE_ACC};
}}

PushButton:disabled, ToolButton:disabled, ToggleToolButton:disabled {{
    color: {TOTONE_MUTE};
    background-color: {TOTONE_BG};
    border-color: {TOTONE_LINE};
}}

ToggleToolButton:checked, TogglePushButton:checked {{
    background-color: {TOTONE_ACC};
    border-color: {TOTONE_ACC};
    color: {TOTONE_ACC_INK};
    font-weight: 700;
}}

/* Totone Primary Buttons — pure white fill with deep navy ink */
PrimaryPushButton, PrimaryToolButton, PrimaryDropDownPushButton, PrimarySplitPushButton {{
    color: {TOTONE_ACC_INK};
    background-color: {TOTONE_ACC};
    border: 1px solid {TOTONE_ACC};
    border-radius: 3px;
    font-weight: 700;
    padding: 5px 12px;
}}

PrimaryPushButton:hover, PrimaryToolButton:hover {{
    background-color: #dbe4ff;
    border-color: #dbe4ff;
    color: {TOTONE_ACC_INK};
}}

PrimaryPushButton:pressed, PrimaryToolButton:pressed {{
    background-color: #c2d1ff;
    border-color: #c2d1ff;
    color: {TOTONE_ACC_INK};
}}

PrimaryPushButton:disabled, PrimaryToolButton:disabled {{
    background-color: {TOTONE_LINE};
    border-color: {TOTONE_LINE};
    color: {TOTONE_MUTE};
}}

TransparentToolButton, TransparentPushButton, HyperlinkButton {{
    color: {TOTONE_INK};
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
}}

TransparentToolButton:hover, TransparentPushButton:hover, HyperlinkButton:hover {{
    background-color: {TOTONE_LINE};
    border-color: {TOTONE_EDGE};
}}

/* Inputs, Search, Combos, SpinBoxes */
LineEdit, SearchLineEdit, PasswordLineEdit, TextEdit, PlainTextEdit,
ComboBox, EditableComboBox, SpinBox, DoubleSpinBox {{
    color: {TOTONE_INK};
    background-color: {TOTONE_BG};
    border: 1px solid {TOTONE_EDGE};
    border-radius: 3px;
    padding: 4px 8px;
}}

LineEdit:hover, SearchLineEdit:hover, ComboBox:hover, SpinBox:hover, TextEdit:hover, PlainTextEdit:hover {{
    border-color: {TOTONE_MUTE};
}}

LineEdit:focus, SearchLineEdit:focus, ComboBox:focus, SpinBox:focus, TextEdit:focus, PlainTextEdit:focus {{
    border: 1px solid {TOTONE_ACC};
    background-color: {TOTONE_BG};
}}

/* Cards: TaskCard, SettingCard, CardWidget */
CardWidget, TaskCard, SettingCard, SimpleCardWidget, HeaderCardWidget, ExpandSettingCard {{
    background-color: {TOTONE_PANEL};
    border: 1px solid {TOTONE_LINE};
    border-radius: 4px;
}}

CardWidget:hover, TaskCard:hover, SettingCard:hover {{
    border: 1px solid {TOTONE_EDGE};
    background-color: #0c1b42;
}}

/* Segmented / Tab Controls (Totone underline / pill tabs) */
SegmentedWidget, SegmentedToggleToolWidget, Pivot {{
    background-color: {TOTONE_PANEL};
    border: 1px solid {TOTONE_LINE};
    border-radius: 4px;
}}

SegmentedItem, PivotItem {{
    color: {TOTONE_MUTE};
    font-weight: 600;
    border-radius: 3px;
}}

SegmentedItem:hover, PivotItem:hover {{
    color: {TOTONE_INK};
}}

SegmentedItem[isSelected=true], PivotItem[isSelected=true] {{
    color: {TOTONE_ACC_INK};
    background-color: {TOTONE_ACC};
    font-weight: 700;
}}

/* Labels & Typography */
CaptionLabel {{
    color: {TOTONE_MUTE};
    background: transparent;
}}

BodyLabel, StrongBodyLabel, SubtitleLabel, TitleLabel, LargeTitleLabel, DisplayLabel {{
    color: {TOTONE_INK};
    background: transparent;
}}

/* Progress Bars — Totone slim pill bar */
ProgressBar, IndeterminateProgressBar {{
    background-color: {TOTONE_BG};
    border: 1px solid {TOTONE_LINE};
    border-radius: 3px;
    min-height: 5px;
    max-height: 6px;
}}

/* Menus, Flyouts, Command Bars, Tooltips */
RoundMenu, CheckableMenu, CommandBarView, FlyoutView, FlyoutViewBase {{
    background-color: {TOTONE_PANEL};
    border: 1px solid {TOTONE_EDGE};
    border-radius: 5px;
}}

QMenu {{
    background-color: {TOTONE_PANEL};
    border: 1px solid {TOTONE_EDGE};
    border-radius: 5px;
    padding: 4px;
}}

QMenu::item {{
    color: {TOTONE_INK};
    padding: 6px 12px;
    border-radius: 3px;
}}

QMenu::item:selected {{
    background-color: {TOTONE_LINE};
}}

QToolTip {{
    background-color: {TOTONE_PANEL};
    color: {TOTONE_INK};
    border: 1px solid {TOTONE_EDGE};
    border-radius: 3px;
    padding: 4px 8px;
}}

/* InfoBars / Toasts */
InfoBar {{
    background-color: {TOTONE_PANEL};
    border: 1px solid {TOTONE_EDGE};
    border-radius: 5px;
}}

/* Dialogs & MessageBoxes */
QDialog, MessageBox, MessageBoxBase {{
    background-color: {TOTONE_PANEL};
    border: 1px solid {TOTONE_EDGE};
    border-radius: 5px;
}}

QFrame#centerWidget, QWidget#widget {{
    background-color: {TOTONE_PANEL};
    border: 1px solid {TOTONE_EDGE};
    border-radius: 5px;
}}

/* ScrollAreas & Slim Navy ScrollBars */
QScrollArea, ScrollArea, SingleDirectionScrollArea, FastScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: {TOTONE_PANEL};
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {TOTONE_EDGE};
    min-height: 28px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {TOTONE_MUTE};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0;
}}

QScrollBar:horizontal {{
    background: {TOTONE_PANEL};
    height: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: {TOTONE_EDGE};
    min-width: 28px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {TOTONE_MUTE};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
    width: 0;
}}

/* Tree / List / Table Views */
QTreeView, QListView, QTableView, TreeView, ListView, TableView {{
    background-color: {TOTONE_BG};
    alternate-background-color: {TOTONE_PANEL};
    border: 1px solid {TOTONE_LINE};
    border-radius: 4px;
    color: {TOTONE_INK};
}}

QTreeView::item:hover, QListView::item:hover, QTableView::item:hover {{
    background-color: {TOTONE_LINE};
}}

QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {{
    background-color: {TOTONE_ACC};
    color: {TOTONE_ACC_INK};
}}
"""


def buildTotonePalette() -> QPalette:
    """Build a QPalette matching Totone's deep midnight navy studio palette."""
    palette = QPalette()
    bg = QColor(TOTONE_BG)
    panel = QColor(TOTONE_PANEL)
    ink = QColor(TOTONE_INK)
    mute = QColor(TOTONE_MUTE)
    line = QColor(TOTONE_LINE)
    acc = QColor(TOTONE_ACC)
    accInk = QColor(TOTONE_ACC_INK)

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
    palette.setColor(QPalette.ColorRole.Light, QColor(TOTONE_EDGE))

    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, mute)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, mute)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, mute)
    return palette


def applyTotoneTheme(application: QApplication) -> None:
    """Apply the Totone deep navy dark theme, palette, typography, and QSS."""
    from qfluentwidgets import Theme, setTheme, setThemeColor

    setTheme(Theme.DARK, save=False)
    # Crisp high-contrast white accent matching Totone (--acc: #ffffff)
    setThemeColor(QColor(TOTONE_ACC), save=False)

    application.setPalette(buildTotonePalette())

    font = QFont()
    font.setFamilies(TOTONE_FONT_FAMILIES)
    font.setPointSize(10)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    application.setFont(font)

    existing = application.styleSheet() or ""
    if "Dodown — Totone Studio UI Theme" not in existing:
        application.setStyleSheet(existing + "\n" + TOTONE_QSS)


def styleWindowTotone(window: QWidget) -> None:
    """Apply Totone window-level dark navy chrome and background colors."""
    if hasattr(window, "setCustomBackgroundColor"):
        window.setCustomBackgroundColor(QColor(TOTONE_BG), QColor(TOTONE_BG))
    if hasattr(window, "setMicaEffectEnabled"):
        window.setMicaEffectEnabled(False)
    window.setWindowIcon(dodownIcon())
