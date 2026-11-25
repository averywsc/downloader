from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget,
)

from app.view.totone_theme import currentPalette


@dataclass
class PaletteAction:
    title: str
    category: str
    callback: Callable[[], None]
    keywords: str = ""


URL_PREFIXES = ("http://", "https://", "magnet:", "ftp://", "ftps://", "ed2k://")


class CommandPaletteDialog(QDialog):
    """Totone-style Spotlight Command Palette (Ctrl+K) with direct URL paste support."""

    def __init__(
        self,
        actions: list[PaletteAction],
        onUrlSubmitted: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._actions = actions
        self._onUrlSubmitted = onUrlSubmitted
        self._visibleActions: list[PaletteAction] = []

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setFixedWidth(540)

        p = currentPalette()
        self.setStyleSheet(
            f"QDialog {{ background-color: {p.panel}; border: 1px solid {p.edge}; border-radius: 6px; }}"
            f"QLineEdit {{ background-color: {p.bg}; color: {p.ink}; border: 1px solid {p.edge}; "
            f"border-radius: 4px; padding: 9px 12px; font-size: 13.5px; }}"
            f"QLineEdit:focus {{ border: 1px solid {p.acc}; }}"
            f"QListWidget {{ background-color: {p.bg}; border: 1px solid {p.line}; border-radius: 4px; "
            f"outline: none; padding: 4px; }}"
            f"QListWidget::item {{ padding: 8px 10px; border-radius: 3px; color: {p.ink}; }}"
            f"QListWidget::item:selected {{ background-color: {p.acc}; color: {p.accink}; font-weight: 700; }}"
            f"QLabel#paletteHint {{ color: {p.mute}; font-size: 11px; }}"
        )

        self.searchEdit = QLineEdit(self)
        self.searchEdit.setPlaceholderText("Type a command, switch theme, or paste a download URL...")

        self.listWidget = QListWidget(self)
        self.listWidget.setMaximumHeight(340)

        self.hintLabel = QLabel("↑/↓ Navigate  ·  Enter Run  ·  Esc Close  ·  Paste URL to download immediately", self)
        self.hintLabel.setObjectName("paletteHint")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)
        layout.addWidget(self.searchEdit)
        layout.addWidget(self.listWidget)
        layout.addWidget(self.hintLabel)

        self.searchEdit.textChanged.connect(self._refreshList)
        self.listWidget.itemActivated.connect(lambda _: self._executeSelected())
        self.searchEdit.installEventFilter(self)

        self._refreshList("")
        self.searchEdit.setFocus()

    def _isUrl(self, text: str) -> bool:
        low = text.strip().lower()
        return any(low.startswith(pref) for pref in URL_PREFIXES)

    def _refreshList(self, query: str) -> None:
        self.listWidget.clear()
        self._visibleActions.clear()
        q = query.strip().lower()

        if self._isUrl(query) and self._onUrlSubmitted is not None:
            url = query.strip()
            act = PaletteAction(
                title=f"Download URL: {url[:64]}{'…' if len(url) > 64 else ''}",
                category="DOWNLOAD",
                callback=lambda u=url: self._onUrlSubmitted(u),
            )
            self._visibleActions.append(act)
            self.listWidget.addItem(QListWidgetItem(f"[{act.category}]  {act.title}"))

        for action in self._actions:
            hay = f"{action.title} {action.category} {action.keywords}".lower()
            if not q or all(tok in hay for tok in q.split()):
                self._visibleActions.append(action)
                self.listWidget.addItem(QListWidgetItem(f"[{action.category}]  {action.title}"))

        if self.listWidget.count() > 0:
            self.listWidget.setCurrentRow(0)

    def _executeSelected(self) -> None:
        row = self.listWidget.currentRow()
        if 0 <= row < len(self._visibleActions):
            action = self._visibleActions[row]
            self.accept()
            action.callback()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.searchEdit and isinstance(event, QKeyEvent) and event.type() == QKeyEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Down:
                if self.listWidget.count() > 0:
                    self.listWidget.setCurrentRow((self.listWidget.currentRow() + 1) % self.listWidget.count())
                return True
            if key == Qt.Key.Key_Up:
                if self.listWidget.count() > 0:
                    self.listWidget.setCurrentRow((self.listWidget.currentRow() - 1) % self.listWidget.count())
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._executeSelected()
                return True
            if key == Qt.Key.Key_Escape:
                self.reject()
                return True
        return super().eventFilter(obj, event)
