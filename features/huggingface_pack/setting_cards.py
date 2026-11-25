"""HuggingFace 加速的设置卡片（View）。config.py 只留配置数据。"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from qfluentwidgets import (
    ComboBox, FluentIcon, HyperlinkButton, LineEdit, PasswordLineEdit,
    SettingCard, ToolButton, ToolTipFilter,
)

from .config import (
    CUSTOM_SITE_KEY,
    MIRROR_SITES,
    TOKEN_URL,
    huggingFaceConfig,
    probeMirrorLatencies,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class HuggingFaceMirrorSiteCard(SettingCard):
    def __init__(self, submit: Callable[..., str], parent: QWidget | None = None):
        self.submit = submit
        super().__init__(
            FluentIcon.GLOBE, self.tr('Mirror Site'),
            self.tr('Select HuggingFace mirror site; latency is for reference only'), parent,
        )
        self._latencies: dict[str, int | None] = {s: None for s in MIRROR_SITES}
        self._isRefreshing = False
        self.comboBox = ComboBox(self)
        self.customSiteEdit = LineEdit(self)
        self.refreshButton = ToolButton(FluentIcon.SYNC, self)

        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        self.comboBox.setMinimumWidth(260)
        self.customSiteEdit.setPlaceholderText("https://example.com/")
        self.customSiteEdit.setClearButtonEnabled(True)
        self.customSiteEdit.setMinimumWidth(220)
        self.refreshButton.setToolTip(self.tr('Re-test Latency'))
        self.refreshButton.installEventFilter(ToolTipFilter(self.refreshButton))

        for site in MIRROR_SITES:
            self.comboBox.addItem(urlparse(site).netloc or site.rstrip("/"))
        self.comboBox.addItem(self.tr('Custom'))

        currentSite = huggingFaceConfig.selectedSite.value
        if currentSite == CUSTOM_SITE_KEY:
            self.comboBox.setCurrentIndex(len(MIRROR_SITES))
        elif currentSite in MIRROR_SITES:
            self.comboBox.setCurrentIndex(MIRROR_SITES.index(currentSite))
        else:
            self.comboBox.setCurrentIndex(0)
        self.customSiteEdit.setText(huggingFaceConfig.customSite.value)
        self.customSiteEdit.setVisible(currentSite == CUSTOM_SITE_KEY)

    def _initLayout(self) -> None:
        self.hBoxLayout.addWidget(self.comboBox)
        self.hBoxLayout.addSpacing(8)
        self.hBoxLayout.addWidget(self.customSiteEdit)
        self.hBoxLayout.addSpacing(8)
        self.hBoxLayout.addWidget(self.refreshButton)
        self.hBoxLayout.addSpacing(16)

    def _bind(self) -> None:
        self.comboBox.currentIndexChanged.connect(self._onCurrentIndexChanged)
        self.customSiteEdit.editingFinished.connect(self._onCustomSiteEditingFinished)
        self.refreshButton.clicked.connect(self.refreshLatencies)

    def _refreshLatencyLabels(self) -> None:
        for i, site in enumerate(MIRROR_SITES):
            displayName = urlparse(site).netloc or site.rstrip("/")
            latency = self._latencies.get(site)
            if latency is None:
                label = displayName
            elif latency < 0:
                label = f"{displayName} ({self.tr('超时')})"
            else:
                label = f"{displayName} ({latency} ms)"
            self.comboBox.setItemText(i, label)

        customSite = huggingFaceConfig.customSite.value
        customLatency = self._latencies.get(customSite) if customSite else None
        if customLatency is None:
            customLabel = self.tr('Custom')
        elif customLatency < 0:
            customLabel = f"{self.tr('自定义')} ({self.tr('超时')})"
        else:
            customLabel = f"{self.tr('自定义')} ({customLatency} ms)"
        self.comboBox.setItemText(len(MIRROR_SITES), customLabel)

    def _onCurrentIndexChanged(self, index: int) -> None:
        from app.config.cfg import cfg
        if index < 0:
            return
        if index < len(MIRROR_SITES):
            cfg.set(huggingFaceConfig.selectedSite, MIRROR_SITES[index])
        else:
            cfg.set(huggingFaceConfig.selectedSite, CUSTOM_SITE_KEY)
        self.customSiteEdit.setVisible(index >= len(MIRROR_SITES))

    def _onCustomSiteEditingFinished(self) -> None:
        from app.config.cfg import cfg
        cfg.set(huggingFaceConfig.customSite, self.customSiteEdit.text().strip())

    def refreshLatencies(self) -> None:
        if self._isRefreshing:
            return
        self._isRefreshing = True
        self._latencies = {s: None for s in MIRROR_SITES}
        self._refreshLatencyLabels()
        self.refreshButton.setEnabled(False)
        self.submit(
            probeMirrorLatencies(),
            done=self._onLatenciesDone, failed=self._onLatenciesFailed,
            owner=self,
        )

    def _onLatenciesDone(self, latencies: dict[str, int]) -> None:
        self._isRefreshing = False
        self.refreshButton.setEnabled(True)
        self._latencies.update(latencies)
        self._refreshLatencyLabels()

    def _onLatenciesFailed(self, error) -> None:
        self._isRefreshing = False
        self.refreshButton.setEnabled(True)


class HuggingFaceTokenCard(SettingCard):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(
            FluentIcon.FINGERPRINT, self.tr("Access Token"),
            self.tr('Used to download gated models (e.g., Llama, Mistral)'), parent,
        )
        self.tokenEdit = PasswordLineEdit(self)
        self.tokenEdit.setPlaceholderText("hf_xxxxxxxxxxxx")
        self.tokenEdit.setMinimumWidth(240)
        self.tokenEdit.setText(huggingFaceConfig.accessToken.value)
        self.openTokenPageButton = HyperlinkButton(self)
        self.openTokenPageButton.setText(self.tr('Get Token'))
        self.openTokenPageButton.setUrl(TOKEN_URL)

        self.hBoxLayout.addWidget(self.tokenEdit)
        self.hBoxLayout.addSpacing(8)
        self.hBoxLayout.addWidget(self.openTokenPageButton)
        self.hBoxLayout.addSpacing(16)

        self.tokenEdit.editingFinished.connect(self._onTokenEdited)

    def _onTokenEdited(self) -> None:
        from app.config.cfg import cfg
        cfg.set(huggingFaceConfig.accessToken, self.tokenEdit.text().strip())


