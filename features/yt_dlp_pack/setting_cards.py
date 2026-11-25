"""yt-dlp 的设置卡片（View）。config.py 只留配置数据。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QHBoxLayout
from qfluentwidgets import (
    CaptionLabel, FluentIcon, PushButton, SettingCard, ToolButton, ToolTipFilter,
)

from .config import clearCookies, hasCookieFile, saveCookies

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class CookieSettingCard(SettingCard):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            FluentIcon.CERTIFICATE,
            QCoreApplication.translate("YtDlpConfig", "YouTube Cookie"),
            self._statusText(),
            parent,
        )
        self._importButton = PushButton(
            QCoreApplication.translate("YtDlpConfig", 'Import'),
            self,
        )
        self._clearButton = ToolButton(FluentIcon.DELETE, self)
        self._clearButton.setToolTip(
            QCoreApplication.translate("YtDlpConfig", 'Clear Cookie')
        )
        self._clearButton.installEventFilter(ToolTipFilter(self._clearButton))
        self._clearButton.setVisible(hasCookieFile())

        buttonLayout = QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.setSpacing(8)
        buttonLayout.addWidget(self._importButton)
        buttonLayout.addWidget(self._clearButton)
        self.hBoxLayout.addLayout(buttonLayout)
        self.hBoxLayout.addSpacing(16)

        self._importButton.clicked.connect(self._onImportClicked)
        self._clearButton.clicked.connect(self._onClearClicked)

    def _statusText(self) -> str:
        if hasCookieFile():
            return QCoreApplication.translate("YtDlpConfig", 'Imported')
        return QCoreApplication.translate(
            "YtDlpConfig", 'A Cookie is required to download content that requires an account. It is recommended to automatically import it using the browser extension.'
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        self.setContent(self._statusText())
        self._clearButton.setVisible(hasCookieFile())

    def _onImportClicked(self) -> None:
        from qfluentwidgets import MessageBoxBase, SubtitleLabel, PlainTextEdit

        dialog = MessageBoxBase(self.window())
        dialog.widget.setMinimumWidth(500)
        dialog.viewLayout.addWidget(SubtitleLabel(
            QCoreApplication.translate("YtDlpConfig", 'Import YouTube Cookie'),
            dialog,
        ))

        label = CaptionLabel(
            QCoreApplication.translate(
                "YtDlpConfig",
                'After installing the browser extension, login information will be automatically included when downloading YouTube videos, with no manual steps required.\nFor manual import: Open YouTube and log in, press F12 to open Developer Tools, go to the Network tab, find any request, copy the value of the Cookie request header and paste it below.',
            ),
            dialog,
        )
        label.setWordWrap(True)
        dialog.viewLayout.addWidget(label)

        editor = PlainTextEdit(dialog)
        editor.setPlaceholderText("SID=xxx; HSID=xxx; ...")
        editor.setMinimumHeight(120)
        dialog.viewLayout.addWidget(editor)

        if dialog.exec():
            text = editor.toPlainText().strip()
            if text:
                saveCookies(text)
                self._refresh()

    def _onClearClicked(self) -> None:
        clearCookies()
        self._refresh()
