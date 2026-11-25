from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, MessageBoxBase, SubtitleLabel

from app.platform.desktop import openChromiumUrl, revealInFolder
from app.view.totone_theme import currentPalette


class ExtensionInstallDialog(MessageBoxBase):
    """Clean English custom-install guide for the Dodown Browser Extension (no store links, no GIFs)."""

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self._path = path

        self.titleLabel = SubtitleLabel(self.tr('Install Dodown Browser Extension'), self)
        self.subtitleLabel = CaptionLabel(
            self.tr('Dodown unpacked its custom Manifest V3 extension to:\n{0}').format(str(path)), self
        )
        self.stepsWidget = QWidget(self)

        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.widget.setMinimumWidth(540)
        self.yesButton.setText(self.tr('Open Extensions Page & Show Folder'))
        self.cancelButton.setText(self.tr('Close'))
        self._initSteps()

    def _initSteps(self) -> None:
        p = currentPalette()

        def chip(text: str, mono: bool = False) -> str:
            family = " font-family: 'Cascadia Code', Consolas, monospace;" if mono else ""
            return (
                f'<span style="background-color: {p.line}; color: {p.ink}; '
                f'border: 1px solid {p.edge}; border-radius: 3px;{family}">&nbsp;{text}&nbsp;</span>'
            )

        steps = [
            f"Open {chip('chrome://extensions', mono=True)} (or {chip('edge://extensions', mono=True)} / {chip('brave://extensions', mono=True)})",
            f"Turn on {chip('Developer Mode')} in the top-right corner",
            f"Click {chip('Load unpacked')} and select the unpacked {chip('Dodown Extension Folder')} (or drag the folder in)",
            f"Click the {chip('Dodown')} extension icon in your browser toolbar and hit {chip('Auto Pair')}",
        ]

        layout = QVBoxLayout(self.stepsWidget)
        layout.setContentsMargins(0, 8, 0, 4)
        layout.setSpacing(12)
        for index, text in enumerate(steps, 1):
            badge = QLabel(str(index), self.stepsWidget)
            badge.setFixedSize(24, 24)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background: {p.acc}; color: {p.accink}; border-radius: 12px; font-weight: 800;"
            )
            stepLabel = BodyLabel(self.stepsWidget)
            stepLabel.setWordWrap(True)
            stepLabel.setTextFormat(Qt.TextFormat.RichText)
            stepLabel.setText(text)
            row = QHBoxLayout()
            row.setSpacing(12)
            row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(stepLabel, 1, Qt.AlignmentFlag.AlignVCenter)
            layout.addLayout(row)

    def _initLayout(self) -> None:
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.subtitleLabel)
        self.viewLayout.addWidget(self.stepsWidget)

    def _bind(self) -> None:
        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self._onInstall)

    def _onInstall(self) -> None:
        from qfluentwidgets import InfoBar, InfoBarPosition

        revealInFolder(str(self._path))
        if not openChromiumUrl("chrome://extensions"):
            QApplication.clipboard().setText("chrome://extensions")
            InfoBar.info(
                self.tr('Open your browser extensions page'),
                self.tr('chrome://extensions copied to clipboard — paste it into your browser address bar.'),
                duration=5000, position=InfoBarPosition.TOP, parent=self,
            )
