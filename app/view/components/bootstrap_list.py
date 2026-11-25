from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
    InfoBar,
    LineEdit,
    MessageBoxBase,
    PrimaryPushButton,
    PushButton,
    SettingCard,
    SubtitleLabel,
    ToolButton,
    ToolTipFilter,
    TransparentToolButton,
)

from app.bootstrap_list import BootstrapList, SubscriptionStatus
from app.config.cfg import ConfigItem, cfg
from app.view.components.editors import AutoSizingEdit
from app.view.components.scroll_area import ScrollArea

FAILURE_NOTICE_AGE = 7 * 86400
CARD_HEIGHT = 70


def toAgoText(seconds: float) -> str:
    if seconds < 60:
        return QCoreApplication.translate("BootstrapList", 'just now')
    if seconds < 3600:
        return QCoreApplication.translate("BootstrapList", '{0} minutes ago').format(int(seconds // 60))
    if seconds < 86400:
        return QCoreApplication.translate("BootstrapList", '{0} hours ago').format(int(seconds // 3600))
    return QCoreApplication.translate("BootstrapList", '{0} days ago').format(int(seconds // 86400))


def toStatusText(status: SubscriptionStatus | None) -> str:
    if status is None or status.count is None:
        return QCoreApplication.translate("BootstrapList", 'Update failed') if status is not None and status.error else QCoreApplication.translate("BootstrapList", 'Waiting for refresh')
    parts = [QCoreApplication.translate("BootstrapList", '{0} item(s)').format(status.count), QCoreApplication.translate("BootstrapList", 'updated {0}').format(toAgoText(time.time() - status.updatedAt))]
    if status.error:
        parts.append(QCoreApplication.translate("BootstrapList", 'Update failed'))
    return QCoreApplication.translate("BootstrapList", ',').join(parts)


def isSubscriptionUrl(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


class BootstrapListCard(SettingCard):
    def __init__(
        self,
        icon: FluentIcon,
        title: str,
        bootstrapList: BootstrapList,
        sourcesItem: ConfigItem,
        submit: Callable[..., str],
        parent=None,
        *,
        customItem: ConfigItem | None = None,
        probeNetworkText: Callable[[], Awaitable[tuple[str, dict]]] | None = None,
    ):
        super().__init__(icon, title, "", parent)
        self._list = bootstrapList
        self._sourcesItem = sourcesItem
        self._customItem = customItem
        self._submit = submit
        self._probeNetworkText = probeNetworkText
        self._networkText = ""
        self.manageButton = PrimaryPushButton(self.tr('Manage'), self)
        self.refreshButton = ToolButton(FluentIcon.SYNC, self)

        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self):
        self.setFixedHeight(CARD_HEIGHT)
        self.refreshButton.setToolTip(self.tr('Update Now'))
        self.refreshButton.installEventFilter(ToolTipFilter(self.refreshButton))
        if self._list.isRefreshing:
            self._startRefresh()
        else:
            self._refreshContent()
            self.probeNetwork()

    def _initLayout(self):
        self.hBoxLayout.addWidget(self.manageButton, 0)
        self.hBoxLayout.addSpacing(8)
        self.hBoxLayout.addWidget(self.refreshButton, 0)
        self.hBoxLayout.addSpacing(16)

    def _bind(self):
        self.manageButton.clicked.connect(self._onManageClicked)
        self.refreshButton.clicked.connect(self._startRefresh)

    def _refreshContent(self):
        if self._list.isRefreshing:
            self.setContent(self.tr('Updating…'))
            return
        statuses = self._list.statuses()
        cached = [s for s in statuses if s.count is not None]
        hasError = any(s.error for s in statuses)
        parts = [self.tr('{0} subscription(s)').format(len(statuses))]
        if cached:
            newest = max(s.updatedAt for s in cached)
            parts.append(self.tr('{0} item(s) total').format(self._list.entryCount()))
            parts.append(self.tr('updated {0}').format(toAgoText(time.time() - newest)))
            if hasError and time.time() - newest > FAILURE_NOTICE_AGE:
                parts.append(self.tr('Update failed'))
        else:
            parts.append(self.tr('Use Built-in List'))
            if hasError:
                parts.append(self.tr('Update failed'))
        if self._networkText:
            parts.append(self._networkText)
        self.setContent(self.tr(',').join(parts))

    def probeNetwork(self):
        if self._probeNetworkText is not None:
            self._submit(self._probeNetworkText(), done=self._onNetworkProbed, owner=self)

    def _onNetworkProbed(self, probed: tuple[str, dict]):
        text, params = probed
        self._networkText = QCoreApplication.translate("BootstrapList", text).format_map(params)
        self._refreshContent()

    def _startRefresh(self):
        self.refreshButton.setEnabled(False)
        self._submit(self._list.refresh(), done=self._onRefreshed, failed=self._onRefreshed, owner=self)
        self._refreshContent()

    def _onRefreshed(self, _result=None):
        self.refreshButton.setEnabled(True)
        self._refreshContent()
        self.probeNetwork()

    def _onManageClicked(self):
        dialog = BootstrapListDialog(self._list, self._sourcesItem, self._customItem, self.window())
        try:
            if dialog.exec():
                self._startRefresh()
        finally:
            dialog.deleteLater()


class SubscriptionRow(QWidget):
    def __init__(self, url: str, statusText: str, onRemoved: Callable[[SubscriptionRow], None], parent=None):
        super().__init__(parent)
        self.urlEdit = LineEdit(self)
        self.statusLabel = BodyLabel(statusText, self)
        self.deleteButton = TransparentToolButton(FluentIcon.CLOSE, self)
        self.hBoxLayout = QHBoxLayout(self)
        self._onRemoved = onRemoved

        self._initWidget(url)
        self._initLayout()
        self._bind()

    @property
    def url(self) -> str:
        return self.urlEdit.text().strip()

    def _initWidget(self, url: str):
        self.urlEdit.setText(url)
        self.urlEdit.setPlaceholderText("https://")

    def _initLayout(self):
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.setSpacing(8)
        self.hBoxLayout.addWidget(self.urlEdit, 1)
        self.hBoxLayout.addWidget(self.statusLabel)
        self.hBoxLayout.addWidget(self.deleteButton)

    def _bind(self):
        self.deleteButton.clicked.connect(lambda: self._onRemoved(self))


class BootstrapListDialog(MessageBoxBase):
    def __init__(self, bootstrapList: BootstrapList, sourcesItem: ConfigItem,
                 customItem: ConfigItem | None, parent=None):
        super().__init__(parent)
        self._sourcesItem = sourcesItem
        self._customItem = customItem
        self._statuses = {s.url: s for s in bootstrapList.statuses()}
        self._statusTexts = [toStatusText(s) for s in (None, *self._statuses.values())]
        self._rows: list[SubscriptionRow] = []
        self.sourceHeaderLabel = SubtitleLabel(self.tr('Subscription URL'), self.widget)
        self.restoreButton = PushButton(self.tr('Restore Defaults'), self.widget)
        self.addButton = PrimaryPushButton(FluentIcon.ADD, self.tr('Add'), self.widget)
        self.scrollArea = ScrollArea(self.widget)
        self.rowContainer = QWidget(self.scrollArea)
        self.customLabel = SubtitleLabel(self.tr('Custom Entries'), self.widget)
        self.customEdit = AutoSizingEdit(self.widget)
        self.sourceHeaderLayout = QHBoxLayout()
        self.rowLayout = QVBoxLayout(self.rowContainer)

        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self):
        self.widget.setMinimumWidth(720)
        self.yesButton.setText(self.tr('Save & Update'))
        self.cancelButton.setText(self.tr('Cancel'))
        for url in self._sourcesItem.value:
            self._addRow(url)
        self.customLabel.setVisible(self._customItem is not None)
        self.customEdit.setVisible(self._customItem is not None)
        if self._customItem is not None:
            self.customEdit.setPlaceholderText(self.tr('One per line; will not be overwritten by subscription updates'))
            self.customEdit.setPlainText(self._customItem.value)

    def _initLayout(self):
        self.sourceHeaderLayout.setContentsMargins(0, 0, 0, 0)
        self.sourceHeaderLayout.addWidget(self.sourceHeaderLabel)
        self.sourceHeaderLayout.addStretch(1)
        self.sourceHeaderLayout.addWidget(self.restoreButton)
        self.sourceHeaderLayout.addWidget(self.addButton)

        self.rowLayout.setContentsMargins(0, 0, 0, 0)
        self.rowLayout.setSpacing(8)
        self.rowLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scrollArea.setWidget(self.rowContainer)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.enableTransparentBackground()

        self.viewLayout.addLayout(self.sourceHeaderLayout)
        self.viewLayout.addWidget(self.scrollArea)
        self.viewLayout.addSpacing(8)
        self.viewLayout.addWidget(self.customLabel)
        self.viewLayout.addWidget(self.customEdit)

    def _bind(self):
        self.addButton.clicked.connect(self._onAddClicked)
        self.restoreButton.clicked.connect(self._onRestoreClicked)

    def validate(self) -> bool:
        for row in self._rows:
            if not isSubscriptionUrl(row.url):
                InfoBar.error(self.tr('Invalid Subscription URL'), self.tr('Please enter a valid HTTP/HTTPS URL'), parent=self)
                row.urlEdit.setFocus()
                self.scrollArea.scrollTo(row.y())
                return False
        cfg.set(self._sourcesItem, list(dict.fromkeys(row.url for row in self._rows)))
        if self._customItem is not None:
            lines = (line.strip() for line in self.customEdit.toPlainText().splitlines())
            cfg.set(self._customItem, "\n".join(line for line in lines if line))
        return True

    def _addRow(self, url: str) -> SubscriptionRow:
        status = self._statuses.get(url)
        row = SubscriptionRow(url, toStatusText(status), self._onRowRemoved, self.rowContainer)
        row.statusLabel.setToolTip(status.error if status is not None else "")
        row.statusLabel.setFixedWidth(max(map(row.statusLabel.fontMetrics().horizontalAdvance, self._statusTexts)))
        self.rowLayout.addWidget(row)
        self._rows.append(row)
        return row

    def _onAddClicked(self):
        row = self._addRow("")
        row.show()
        row.urlEdit.setFocus()
        self.rowContainer.adjustSize()
        self.scrollArea.scrollTo(row.y())

    def _onRowRemoved(self, row: SubscriptionRow):
        self._rows.remove(row)
        self.rowLayout.removeWidget(row)
        row.deleteLater()

    def _onRestoreClicked(self):
        for row in list(self._rows):
            self._onRowRemoved(row)
        for url in self._sourcesItem.defaultValue:
            self._addRow(url)
