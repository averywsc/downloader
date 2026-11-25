from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QCoreApplication, QRect, QRectF, QSize, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QMovie, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    BodyLabel, CaptionLabel, CardWidget, CheckBox, ComboBox,
    DrillInTransitionStackedWidget, FluentIcon, FluentWidget,
    GroupHeaderCardWidget, HorizontalPipsPager, IconWidget, InfoBar,
    InfoBarIcon, InfoBarPosition, PipsScrollButtonDisplayMode,
    PrimaryPushButton, PushButton, SubtitleLabel, SwitchButton, Theme,
    TitleLabel, TransparentPushButton, isDarkTheme, qconfig, themeColor,
)
from qfluentwidgets import MSFluentTitleBar
from qfluentwidgets.common.style_sheet import updateStyleSheet

from app.config.cfg import cfg
from app.i18n import toLanguageText, toLocalizedError
from app.models.task import toTaskError
from app.platform.desktop import openChromiumUrl, revealInFolder
from app.platform.file_association import registerUrlScheme, unregisterUrlScheme
from app.platform.run_at_login import setRunAtLogin
from app.services.port_listener import ListenStatus
from app.config.constants import LATEST_EXTENSION_VERSION

if sys.platform == "win32":
    from ctypes import cast, POINTER
    from ctypes.wintypes import MSG

    import win32con
    from qframelesswindow.windows.c_structures import PWINDOWPOS

if TYPE_CHECKING:
    from app.services.browser_service import PairRequest
    from app.models.pack import BinaryRuntime

WINDOW_SIZE = QSize(960, 600)
PREVIEW_SIZE = QSize(540, 280)
STORE_COLUMN_WIDTH = 300

NEUTRAL_CHIP_COLORS = ("#EFEFEF", "#666666", "#16254d", "#8d9cc4")
SUCCESS_CHIP_COLORS = ("#E8F5E9", "#0F7B46", "#0e2a2f", "#4ADE80")


class IconChip(QWidget):

    def __init__(self, icon: FluentIcon, colors: tuple[str, str, str, str],
                 size: int = 40, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._colors = colors
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        lightBg, lightFg, darkBg, darkFg = self._colors
        bg, fg = (darkBg, darkFg) if isDarkTheme() else (lightBg, lightFg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(self.rect(), 8, 8)
        margin = round(self.width() * 0.25)
        iconRect = self.rect().adjusted(margin, margin, -margin, -margin)
        self._icon.render(painter, iconRect, fill=fg)


class ThemePreview(QWidget):

    def __init__(self, mode: str, parent=None):
        super().__init__(parent)
        self._mode = mode
        self.setFixedHeight(96)

    def _drawMini(self, painter: QPainter, rect: QRectF, isDark: bool) -> None:
        bg = QColor("#050c1f") if isDark else QColor("#F5F7FA")
        titleBar = QColor("#091534") if isDark else QColor("#E9EDF2")
        bar = QColor("#16254d") if isDark else QColor("#FFFFFF")

        painter.fillRect(rect, bg)
        painter.fillRect(QRectF(rect.x(), rect.y(), rect.width(), 14), titleBar)

        padding = 8
        barX = rect.x() + padding
        barWidth = rect.width() - padding * 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bar)
        painter.drawRoundedRect(QRectF(barX, rect.y() + 22, barWidth, 9), 3, 3)
        painter.drawRoundedRect(QRectF(barX, rect.y() + 37, barWidth * 0.55, 9), 3, 3)
        painter.setBrush(themeColor())
        painter.drawRoundedRect(
            QRectF(barX, rect.y() + rect.height() - 20, barWidth * 0.34, 11), 3, 3
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        outer = QRectF(self.rect())
        clipPath = QPainterPath()
        clipPath.addRoundedRect(outer, 6, 6)
        painter.setClipPath(clipPath)

        if self._mode == "auto":
            half = outer.width() / 2
            self._drawMini(painter, QRectF(outer.x(), outer.y(), half, outer.height()), isDark=False)
            self._drawMini(painter, QRectF(outer.x() + half, outer.y(), half, outer.height()), isDark=True)
        else:
            self._drawMini(painter, outer, isDark=self._mode == "dark")

        painter.setClipping(False)
        painter.setPen(QPen(QColor(128, 128, 128, 60), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(outer.adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)


class ThemeCard(CardWidget):

    def __init__(self, theme: Theme, label: str, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._isSelected = False
        self._initWidget(label)
        self._initLayout()

    def _initWidget(self, label: str) -> None:
        self.setClickEnabled(True)
        mode = {Theme.LIGHT: "light", Theme.DARK: "dark"}.get(self.theme, "auto")
        self.preview = ThemePreview(mode, self)
        self.label = BodyLabel(label, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _initLayout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)
        layout.addWidget(self.preview)
        layout.addWidget(self.label)

    def setSelected(self, isSelected: bool) -> None:
        self._isSelected = isSelected
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._isSelected:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(themeColor(), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        radius = self.borderRadius
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)


class ActionCard(CardWidget):

    def __init__(self, icon: FluentIcon, title: str, hint: str = "",
                 isRecommended: bool = False, parent=None):
        super().__init__(parent)
        self._isRecommended = isRecommended
        self._initWidget(icon, title, hint)
        self._initLayout()

    def _initWidget(self, icon: FluentIcon, title: str, hint: str) -> None:
        self.setClickEnabled(True)
        if hint:
            self.setMinimumHeight(80)
        else:
            self.setFixedHeight(48)
        self.iconChip = IconChip(icon, NEUTRAL_CHIP_COLORS, size=30, parent=self)
        self.titleLabel = BodyLabel(title, self)
        self.hintLabel = None
        if hint:
            self.hintLabel = CaptionLabel(hint, self)
            self.hintLabel.setTextColor(Qt.GlobalColor.gray, Qt.GlobalColor.gray)
            self.hintLabel.setWordWrap(True)
        self.chevron = IconWidget(FluentIcon.CHEVRON_RIGHT_MED, self)
        self.chevron.setFixedSize(12, 12)

    def _initLayout(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)
        layout.addWidget(self.iconChip)

        textCol = QVBoxLayout()
        textCol.setSpacing(2)
        textCol.addWidget(self.titleLabel)
        if self.hintLabel is not None:
            textCol.addWidget(self.hintLabel)
        layout.addLayout(textCol, 1)
        layout.addWidget(self.chevron)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._isRecommended:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(themeColor(), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        radius = self.borderRadius
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)


class OptionCard(CardWidget):

    def __init__(self, icon: FluentIcon, title: str, desc: str,
                 isChecked: bool = False, parent=None):
        super().__init__(parent)
        self._initWidget(icon, title, desc, isChecked)
        self._initLayout()

    def _initWidget(self, icon: FluentIcon, title: str, desc: str, isChecked: bool) -> None:
        self.setFixedHeight(64)
        self.iconChip = IconChip(icon, NEUTRAL_CHIP_COLORS, size=34, parent=self)
        self.titleLabel = BodyLabel(title, self)
        self.descLabel = CaptionLabel(desc, self)
        self.descLabel.setTextColor(Qt.GlobalColor.gray, Qt.GlobalColor.gray)
        self.switch = SwitchButton(self)
        self.switch.setOnText("")
        self.switch.setOffText("")
        self.switch.setChecked(isChecked)

    def _initLayout(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(14)
        layout.addWidget(self.iconChip)

        textCol = QVBoxLayout()
        textCol.setSpacing(0)
        textCol.addWidget(self.titleLabel)
        textCol.addWidget(self.descLabel)
        layout.addLayout(textCol, 1)
        layout.addWidget(self.switch)

    def isChecked(self) -> bool:
        return self.switch.isChecked()


class PageHeader(QWidget):

    def __init__(self, title: str, desc: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(SubtitleLabel(title, self))
        descLabel = CaptionLabel(desc, self)
        descLabel.setTextColor(Qt.GlobalColor.gray, Qt.GlobalColor.gray)
        layout.addWidget(descLabel)


class WelcomePage(QWidget):

    startClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        self.iconLabel = QLabel(self)
        from app.view.totone_theme import dodownIcon
        self.iconLabel.setPixmap(dodownIcon().pixmap(88, 88))
        self.iconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.titleLabel = TitleLabel(self.tr('Welcome to Dodown'), self)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.subtitleLabel = BodyLabel(
            self.tr('A fast, smart download manager.\nThe next steps will guide you through the basic setup.'), self
        )
        self.subtitleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitleLabel.setWordWrap(True)

        self.startButton = PrimaryPushButton(self.tr('Start Setup'), self)
        self.startButton.setFixedWidth(200)

    def _initLayout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addStretch(3)
        layout.addWidget(self.iconLabel, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(16)
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.subtitleLabel)
        layout.addSpacing(28)
        layout.addWidget(self.startButton, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(4)

    def _bind(self) -> None:
        self.startButton.clicked.connect(self.startClicked)


class BasicSettingsPage(QWidget):

    languageChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        self.header = PageHeader(
            self.tr('Basic Settings'),
            self.tr('Choose your preferred appearance and set the download location'), self,
        )

        self._themeCards: list[ThemeCard] = []
        for theme, label in [(Theme.LIGHT, self.tr('Light')),
                              (Theme.DARK, self.tr('Dark')),
                              (Theme.AUTO, self.tr('Follow System'))]:
            self._themeCards.append(ThemeCard(theme, label, self))
        self._refreshThemeCards()

        self.settingsCard = GroupHeaderCardWidget(self.tr('Preferences'), self)

        self.langCombo = ComboBox(self)
        self.langCombo.setMinimumWidth(200)
        langOptions = cfg.language.options
        if cfg.language.value not in langOptions:
            cfg.language.value = "en_US" if "en_US" in langOptions else langOptions[0]
        self.langCombo.addItems([self.tr('Use System Settings'), *map(toLanguageText, langOptions[1:])])
        self.langCombo.setCurrentIndex(langOptions.index(cfg.language.value))

        self.browseButton = PushButton(self.tr('Browse...'), self)

    def _initLayout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addStretch(1)

        themeRow = QHBoxLayout()
        themeRow.setSpacing(14)
        for card in self._themeCards:
            themeRow.addWidget(card)
        layout.addLayout(themeRow)
        layout.addStretch(1)

        self.settingsCard.addGroup(
            FluentIcon.LANGUAGE, self.tr('Interface Language'),
            self.tr('Changes take effect immediately'), self.langCombo,
        )
        self._folderGroup = self.settingsCard.addGroup(
            FluentIcon.FOLDER, self.tr('Download Location'),
            str(cfg.downloadFolder.value), self.browseButton,
        )
        layout.addWidget(self.settingsCard)
        layout.addStretch(1)

    def _bind(self) -> None:
        for card in self._themeCards:
            card.clicked.connect(lambda t=card.theme: self._onThemePicked(t))
        self.langCombo.currentIndexChanged.connect(self._onLanguageChanged)
        self.browseButton.clicked.connect(self._onBrowseClicked)

    def _onThemePicked(self, theme: Theme) -> None:
        cfg.set(cfg.themeMode, theme)
        updateStyleSheet()
        qconfig.themeChangedFinished.emit()
        self._refreshThemeCards()

    def _refreshThemeCards(self) -> None:
        current = cfg.themeMode.value
        for card in self._themeCards:
            card.setSelected(card.theme == current)

    def _onLanguageChanged(self, index: int) -> None:
        options = cfg.language.options
        if 0 <= index < len(options) and options[index] != cfg.language.value:
            cfg.set(cfg.language, options[index])
            self.languageChanged.emit()

    def _onBrowseClicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.tr('Choose Download Directory'), str(cfg.downloadFolder.value)
        )
        if folder:
            cfg.set(cfg.downloadFolder, folder)
            self._folderGroup.setContent(folder)


class BrowserExtensionPage(QWidget):

    def __init__(self, browserService, browserListener, coroutineRunner, parent=None):
        super().__init__(parent)
        self._browserService = browserService
        self._browserListener = browserListener
        self._coroutineRunner = coroutineRunner
        self._isPaired = False
        self._banner: InfoBar | None = None
        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        self.header = PageHeader(
            self.tr('Install Browser Extension'),
            self.tr('Automatically take over downloads from your browser to Dodown'), self,
        )

        self.previewLabel = QLabel(self)
        self.previewLabel.setFixedSize(PREVIEW_SIZE)
        self.previewLabel.setWordWrap(True)
        self.previewLabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.previewLabel.setText(
            "<b>Custom Dodown Browser Extension (Manifest V3)</b><br><br>"
            "1. Click <b>Install Dodown Extension</b> on the right to unpack it.<br><br>"
            "2. Open <code>chrome://extensions</code> (or Edge / Brave / Arc).<br><br>"
            "3. Enable <b>Developer Mode</b> and click <b>Load unpacked</b>.<br><br>"
            "4. Open the <b>Dodown</b> extension popup and click <b>Auto Pair</b>."
        )
        self.previewLabel.setStyleSheet(
            "QLabel { background: #091534; color: #f4f7ff; border: 1px solid #16254d; "
            "border-radius: 5px; padding: 20px; font-size: 13px; }"
        )

        self.manualCard = ActionCard(
            FluentIcon.DOWNLOAD, self.tr('Install Dodown Extension'),
            self.tr('Unpacks Dodown\'s custom Manifest V3 extension for Chrome, Edge, Brave, and other Chromium browsers'),
            isRecommended=True, parent=self,
        )
        self.storeCards: list[tuple[ActionCard, str]] = []

        self.footnote = CaptionLabel(self.tr('100% local & custom-built for Dodown — no external store account required.'), self)
        self.footnote.setTextColor(Qt.GlobalColor.gray, Qt.GlobalColor.gray)

    def _initLayout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addStretch(1)

        contentLayout = QHBoxLayout()
        contentLayout.setSpacing(16)

        leftLayout = QVBoxLayout()
        leftLayout.setSpacing(10)
        leftLayout.addWidget(self.previewLabel)
        self._bannerSlot = QVBoxLayout()
        self._bannerSlot.setContentsMargins(0, 0, 0, 0)
        leftLayout.addLayout(self._bannerSlot)
        contentLayout.addLayout(leftLayout)

        rightWidget = QWidget(self)
        rightWidget.setFixedWidth(STORE_COLUMN_WIDTH)
        rightLayout = QVBoxLayout(rightWidget)
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.setSpacing(10)
        rightLayout.addStretch(1)
        rightLayout.addWidget(self.manualCard)
        for card, _ in self.storeCards:
            rightLayout.addWidget(card)
        rightLayout.addWidget(self.footnote)
        rightLayout.addStretch(1)
        contentLayout.addWidget(rightWidget)

        layout.addLayout(contentLayout)
        layout.addStretch(1)

    def _bind(self) -> None:
        self.manualCard.clicked.connect(self._onManualInstallClicked)
        for card, url in self.storeCards:
            card.clicked.connect(lambda u=url: QDesktopServices.openUrl(QUrl(u)))
        self._browserService.connectionChanged.connect(self._onConnectionChanged, owner=self)
        self._browserService.protocolMismatched.connect(self._onProtocolMismatched, owner=self)
        self._browserListener.stateChanged.connect(self._onListenStateChanged, owner=self)

    def _setBanner(self, icon: InfoBarIcon, title: str) -> None:
        if self._banner is not None:
            self._bannerSlot.removeWidget(self._banner)
            self._banner.deleteLater()
        self._banner = InfoBar(
            icon, title, "", isClosable=False,
            duration=-1, position=InfoBarPosition.NONE, parent=self,
        )
        self._banner.contentLabel.hide()
        self._banner.setFixedWidth(PREVIEW_SIZE.width())
        self._bannerSlot.addWidget(self._banner)

    def refreshListenState(self) -> None:
        if self._isPaired:
            return
        state = self._browserListener.state
        if state.status == ListenStatus.OFF:
            self._setBanner(
                InfoBarIcon.WARNING,
                self.tr('Browser extension is not enabled; you can turn it on later in Settings'),
            )
        elif state.status == ListenStatus.FAILED:
            self._setBanner(InfoBarIcon.WARNING, toLocalizedError(state.error))
        else:
            self._setBanner(
                InfoBarIcon.INFORMATION,
                self.tr('Waiting for extension connection on port {}').format(state.port),
            )

    def _setConnectedBanner(self, version: str) -> None:
        if version:
            text = self.tr('Extension v{} connected; latest version is v{}').format(
                version, LATEST_EXTENSION_VERSION
            )
        else:
            text = self.tr('Extension connected; latest version is v{}').format(LATEST_EXTENSION_VERSION)
        self._setBanner(InfoBarIcon.SUCCESS, text)

    def _onConnectionChanged(self) -> None:
        installType, version = self._browserService.connectionSummary
        if installType or version:
            self._isPaired = True
            self._setConnectedBanner(version)
        else:
            self._isPaired = False
            self.refreshListenState()

    def _onManualInstallClicked(self) -> None:
        self._coroutineRunner.submit(
            self._browserService.install(),
            done=self._onExtensionExtracted,
            failed=self._onExtensionExtractFailed,
            owner=self,
        )

    def _onExtensionExtracted(self, path: Path) -> None:
        revealInFolder(str(path))
        if not openChromiumUrl("chrome://extensions"):
            QApplication.clipboard().setText("chrome://extensions")
            InfoBar.info(
                self.tr('Please manually open your browser'),
                self.tr('chrome://extensions has been copied to clipboard'),
                duration=5000, position=InfoBarPosition.TOP, parent=self,
            )

    def _onExtensionExtractFailed(self, error) -> None:
        InfoBar.error(
            self.tr('Unpack failed'), toLocalizedError(toTaskError(error)),
            duration=5000, position=InfoBarPosition.TOP, parent=self,
        )

    def onPairRequested(self, request: PairRequest) -> None:
        self._browserService.approvePair(request.requestId)
        self._isPaired = True
        self._setConnectedBanner(request.extensionVersion)

    def _onListenStateChanged(self, _state) -> None:
        if self.isVisible():
            self.refreshListenState()

    def _onProtocolMismatched(self) -> None:
        self._setBanner(
            InfoBarIcon.WARNING,
            self.tr('Protocol version mismatch; the store version may be outdated, please try manual installation'),
        )


class RuntimeInstallPage(QWidget):

    def __init__(self, featureService, parent=None):
        super().__init__(parent)
        self._featureService = featureService
        self._checkBoxes: list[tuple[CheckBox, BinaryRuntime]] = []
        self._isMounted = False
        self._initWidget()
        self._initLayout()

    def _initWidget(self) -> None:
        self.header = PageHeader(
            self.tr('Install Recommended Components'),
            self.tr('Click Next to install the selected components; you can manage them later in Settings'), self,
        )
        self._card = GroupHeaderCardWidget(self.tr('Recommended Components'), self)

    def _initLayout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addStretch(1)
        layout.addWidget(self._card)
        layout.addStretch(1)

    def mount(self) -> None:
        if self._isMounted:
            return
        self._isMounted = True

        entries = [rt for rt in self._featureService.runtimes() if rt.canInstall and rt.title]
        entries.sort(key=lambda rt: not rt.isRecommended)

        for runtime in entries:
            trailing = QWidget(self)
            trailingLayout = QHBoxLayout(trailing)
            trailingLayout.setContentsMargins(0, 0, 0, 0)
            trailingLayout.setSpacing(12)

            tag = CaptionLabel(runtime.name, trailing)
            tag.setTextColor(Qt.GlobalColor.gray, Qt.GlobalColor.gray)
            trailingLayout.addWidget(tag)

            if runtime.path():
                installedLabel = CaptionLabel(self.tr('Installed'), trailing)
                installedLabel.setTextColor(Qt.GlobalColor.darkGreen, Qt.GlobalColor.green)
                trailingLayout.addWidget(installedLabel)
            else:
                checkBox = CheckBox(trailing)
                checkBox.setChecked(runtime.isRecommended)
                trailingLayout.addWidget(checkBox)
                self._checkBoxes.append((checkBox, runtime))

            self._card.addGroup(
                getattr(FluentIcon, runtime.icon, FluentIcon.APPLICATION),
                QCoreApplication.translate("BinaryRuntime", runtime.title),
                QCoreApplication.translate("BinaryRuntime", runtime.description),
                trailing,
            )

    def selectedRuntimes(self) -> list[BinaryRuntime]:
        return [rt for cb, rt in self._checkBoxes if cb.isChecked()]


class AdvancedOptionsPage(QWidget):

    def __init__(self, featureService, parent=None):
        super().__init__(parent)
        self._featureService = featureService
        self._initWidget()
        self._initLayout()

    def _initWidget(self) -> None:
        self.header = PageHeader(
            self.tr('More Options'),
            self.tr('Enable the following features as needed; you can change them later in Settings'), self,
        )
        self.runAtLoginCard = OptionCard(
            FluentIcon.POWER_BUTTON, self.tr('Start on Boot'),
            self.tr('Run automatically at system startup to take over downloads anytime'),
            isChecked=cfg.shouldRunAtLogin.value, parent=self,
        )
        self.clipboardCard = OptionCard(
            FluentIcon.PASTE, self.tr('Monitor Clipboard'),
            self.tr('Take over and handle copied download links'),
            isChecked=cfg.isClipboardListenerEnabled.value, parent=self,
        )
        self.categoryCard = OptionCard(
            FluentIcon.TAG, self.tr('Download Categorization'),
            self.tr('Automatically save files to subfolders (Videos, Audio, Documents, etc.) based on file type'),
            isChecked=cfg.isCategoryEnabled.value, parent=self,
        )
        if sys.platform != "darwin":
            self.fileAssocCard = OptionCard(
                FluentIcon.DOCUMENT, self.tr('Associate File Types'),
                self.tr('Open .torrent and other supported files with Dodown'),
                isChecked=self._featureService.isFileAssociationEnabled(), parent=self,
            )
            self.uriSchemeCard = OptionCard(
                FluentIcon.LINK, self.tr('Associate Special Protocol URLs'),
                self.tr('Open Magnet/eD2k/FTP links with Dodown'),
                isChecked=self._featureService.isUriSchemeAssociationEnabled(), parent=self,
            )
            self.urlSchemeCard = OptionCard(
                FluentIcon.GLOBE, self.tr('Allow Launching From Browser Extension'),
                self.tr('The browser extension may launch the app via dodown:// URL scheme'),
                isChecked=cfg.isUrlSchemeRegistered.value, parent=self,
            )
        else:
            self.fileAssocCard = None
            self.uriSchemeCard = None
            self.urlSchemeCard = None
        self.aria2Card = OptionCard(
            FluentIcon.COMMAND_PROMPT, self.tr('Aria2 RPC Support'),
            self.tr('Allow Aria2-compatible tools and websites send download tasks to Dodown'),
            isChecked=cfg.isAria2RpcEnabled.value, parent=self,
        )

    def _initLayout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addStretch(1)

        listLayout = QVBoxLayout()
        listLayout.setSpacing(8)
        for card in [self.runAtLoginCard, self.clipboardCard, self.categoryCard,
                     self.fileAssocCard, self.uriSchemeCard, self.urlSchemeCard, self.aria2Card]:
            if card is not None:
                listLayout.addWidget(card)
        layout.addLayout(listLayout)
        layout.addStretch(1)

    def save(self) -> None:
        if self.runAtLoginCard.isChecked() != cfg.shouldRunAtLogin.value:
            setRunAtLogin(self.runAtLoginCard.isChecked())
            cfg.set(cfg.shouldRunAtLogin, self.runAtLoginCard.isChecked())

        cfg.set(cfg.isClipboardListenerEnabled, self.clipboardCard.isChecked())

        cfg.set(cfg.isCategoryEnabled, self.categoryCard.isChecked())

        if self.fileAssocCard is not None:
            for pack in self._featureService.packs:
                config = pack.config
                if config is not None and config.associateFileTypes is not None:
                    cfg.set(config.associateFileTypes, self.fileAssocCard.isChecked())
                if config is not None and config.associateUriSchemes is not None:
                    cfg.set(config.associateUriSchemes, self.uriSchemeCard.isChecked())

        if self.urlSchemeCard is not None:
            if self.urlSchemeCard.isChecked():
                registerUrlScheme()
            else:
                unregisterUrlScheme()
            cfg.set(cfg.isUrlSchemeRegistered, self.urlSchemeCard.isChecked())

        cfg.set(cfg.isAria2RpcEnabled, self.aria2Card.isChecked())


class CompletePage(QWidget):

    finishClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        self.checkIcon = IconChip(FluentIcon.ACCEPT, SUCCESS_CHIP_COLORS, size=80, parent=self)

        self.titleLabel = TitleLabel(self.tr('All Set'), self)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.descLabel = BodyLabel(
            self.tr('Dodown is now ready!\nYou can adjust options in Settings at any time.'),
            self,
        )
        self.descLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.descLabel.setWordWrap(True)

        self.finishButton = PrimaryPushButton(self.tr('Get Started'), self)
        self.finishButton.setFixedWidth(200)

    def _initLayout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addStretch(3)
        layout.addWidget(self.checkIcon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(16)
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.descLabel)
        layout.addSpacing(28)
        layout.addWidget(self.finishButton, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(4)

    def _bind(self) -> None:
        self.finishButton.clicked.connect(self.finishClicked)


class OobeWindow(FluentWidget):

    finished = Signal()

    PAGE_COUNT = 6

    def __init__(self, browserService, browserListener, coroutineRunner, featureService,
                 runtimeStatusService, parent=None):
        super().__init__(parent=parent)
        self._browserService = browserService
        self._browserListener = browserListener
        self._coroutineRunner = coroutineRunner
        self._featureService = featureService
        self._runtimeStatusService = runtimeStatusService
        self._currentIndex = 0
        self._isFinished = False
        self._initWidget()
        self._initContent()
        self._initContentLayout()
        self._initLayout()
        self._bind()
        self._refreshNavigation()

    def _initWidget(self) -> None:
        from app.view.totone_theme import dodownIcon, styleWindowTotone
        self.setTitleBar(MSFluentTitleBar(self))
        styleWindowTotone(self)
        self.setWindowTitle('Dodown')
        self.setWindowIcon(dodownIcon())
        if hasattr(self.titleBar, "titleLabel"):
            self.titleBar.titleLabel.setObjectName("totoneBrandTitle")
        self.titleBar.hBoxLayout.insertSpacing(2, 6)
        if sys.platform == "darwin":
            self.titleBar.hBoxLayout.insertSpacing(0, 60)
        self.titleBar.maxBtn.hide()
        self.setFixedSize(WINDOW_SIZE)
        self.setResizeEnabled(False)
        desktop = QApplication.primaryScreen().availableGeometry()
        self.move(desktop.center() - self.rect().center())

    def systemTitleBarRect(self, size) -> QRect:
        return QRect(0, 10, 75, size.height())

    def _initContent(self) -> None:
        self.content = QWidget(self)
        self.welcomePage = WelcomePage(self.content)
        self.basicSettingsPage = BasicSettingsPage(self.content)
        self.browserExtensionPage = BrowserExtensionPage(
            self._browserService, self._browserListener, self._coroutineRunner, self.content)
        self.runtimeInstallPage = RuntimeInstallPage(self._featureService, self.content)
        self.advancedOptionsPage = AdvancedOptionsPage(self._featureService, self.content)
        self.completePage = CompletePage(self.content)

        self.stackedWidget = DrillInTransitionStackedWidget(self.content)
        self.stackedWidget.addWidget(self.welcomePage)
        self.stackedWidget.addWidget(self.basicSettingsPage)
        self.stackedWidget.addWidget(self.browserExtensionPage)
        self.stackedWidget.addWidget(self.runtimeInstallPage)
        self.stackedWidget.addWidget(self.advancedOptionsPage)
        self.stackedWidget.addWidget(self.completePage)

        self.backButton = PushButton(self.tr('Previous'), self.content)
        self.skipButton = TransparentPushButton(self.tr('Skip All'), self.content)
        self.nextButton = PrimaryPushButton(self.tr('Next'), self.content)
        self.pipsPager = HorizontalPipsPager(self.content)
        self.pipsPager.setPageNumber(self.PAGE_COUNT)
        self.pipsPager.setVisibleNumber(self.PAGE_COUNT)
        self.pipsPager.setPreviousButtonDisplayMode(PipsScrollButtonDisplayMode.NEVER)
        self.pipsPager.setNextButtonDisplayMode(PipsScrollButtonDisplayMode.NEVER)
        self.pipsPager.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def _initContentLayout(self) -> None:
        mainLayout = QVBoxLayout(self.content)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        mainLayout.addWidget(self.stackedWidget, 1)

        navLayout = QHBoxLayout()
        navLayout.setContentsMargins(0, 14, 0, 0)

        leftBox = QHBoxLayout()
        leftBox.addWidget(self.skipButton)
        leftBox.addWidget(self.backButton)
        leftBox.addStretch()

        rightBox = QHBoxLayout()
        rightBox.addStretch()
        rightBox.addWidget(self.nextButton)

        navLayout.addLayout(leftBox, 1)
        navLayout.addWidget(self.pipsPager)
        navLayout.addLayout(rightBox, 1)
        mainLayout.addLayout(navLayout)

    def _initLayout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, self.titleBar.height() + 8, 36, 16)
        layout.addWidget(self.content)

    def _bind(self) -> None:
        self.welcomePage.startClicked.connect(self._onNextClicked)
        self.basicSettingsPage.languageChanged.connect(self._onLanguageChanged)
        self.completePage.finishClicked.connect(self._finish)
        self.backButton.clicked.connect(self._onBackClicked)
        self.nextButton.clicked.connect(self._onNextClicked)
        self.skipButton.clicked.connect(self._finish)

    def onPairRequested(self, request: PairRequest) -> None:
        self.browserExtensionPage.onPairRequested(request)

    def _onLanguageChanged(self) -> None:
        old = self.content
        self._initContent()
        self._initContentLayout()
        self.layout().replaceWidget(old, self.content)
        old.hide()
        old.deleteLater()

        self._bind()
        self.stackedWidget.setAnimationEnabled(False)
        self.stackedWidget.setCurrentIndex(self._currentIndex)
        self.stackedWidget.setAnimationEnabled(True)
        self._refreshNavigation()

    def _refreshNavigation(self) -> None:
        i = self._currentIndex
        isFirst = i == 0
        isLast = i == self.PAGE_COUNT - 1

        self.backButton.setVisible(not isFirst and not isLast)
        self.nextButton.setVisible(not isFirst and not isLast)
        self.skipButton.setVisible(isFirst)
        self.pipsPager.setCurrentIndex(i)

    def _onNextClicked(self) -> None:
        if self._currentIndex >= self.PAGE_COUNT - 1:
            return

        if self._currentIndex == 3:
            self._installSelectedRuntimes()

        self._currentIndex += 1
        self.stackedWidget.setCurrentIndex(self._currentIndex)
        self._refreshNavigation()
        if self._currentIndex == 2:
            self.browserExtensionPage.refreshListenState()
        elif self._currentIndex == 3:
            self.runtimeInstallPage.mount()

    def _onBackClicked(self) -> None:
        if self._currentIndex <= 0:
            return
        self._currentIndex -= 1
        self.stackedWidget.setCurrentIndex(self._currentIndex, isBack=True)
        self._refreshNavigation()

    def _installSelectedRuntimes(self) -> None:
        runtimes = self.runtimeInstallPage.selectedRuntimes()
        if not runtimes:
            return

        for runtime in runtimes:
            if runtime.path():
                continue
            self._runtimeStatusService.install(runtime)

    def _finish(self) -> None:
        if self._isFinished:
            return
        self._isFinished = True
        self.advancedOptionsPage.save()
        cfg.set(cfg.hasCompletedOobe, True)
        self.finished.emit()
        self.close()

    def nativeEvent(self, eventType, message):
        if sys.platform == "win32":
            msg = MSG.from_address(message.__int__())
            if msg.message == win32con.WM_WINDOWPOSCHANGING:
                pos = cast(msg.lParam, POINTER(PWINDOWPOS)).contents
                if not (pos.flags & win32con.SWP_NOSIZE):
                    dpr = self.devicePixelRatio()
                    pos.cx = int(WINDOW_SIZE.width() * dpr)
                    pos.cy = int(WINDOW_SIZE.height() * dpr)
        return super().nativeEvent(eventType, message)

    def closeEvent(self, event) -> None:
        if not self._isFinished:
            self._isFinished = True
            cfg.set(cfg.hasCompletedOobe, True)
            self.finished.emit()
        super().closeEvent(event)
