from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    ComboBoxSettingCard, FluentIcon, HyperlinkCard, HyperlinkButton, InfoBar,
    InfoBarPosition, MessageBox, PrimaryPushSettingCard, PushButton, PushSettingCard,
    RangeSettingCard, SwitchSettingCard, ToolButton, ToolTipFilter,
)

from app.view.components.scroll_area import FastScrollArea, PAGE_MARGIN

from app.config.cfg import NoticeStyle, canShowPopup, cfg
from app.i18n import toLanguageText, toLocalizedError
from app.models.task import toTaskError
from app.services.port_listener import ListenStatus
from app.config.constants import (
    AUTHOR, AUTHOR_URL, CHROME_WEBSTORE_URL, EDGE_ADDONS_URL,
    FEEDBACK_URL, FIREFOX_ADDONS_URL, VERSION, YEAR,
)
from app.view.components.category_settings import CategoryRulesCard
from app.view.components.setting_card_group import (
    CollapsibleSettingCardGroup, SettingGroupNav, groupsIn, restoreGroupOrder,
)
from app.view.components.setting_cards import (
    AssociationCard, ClipboardSettingCard, HeadersPresetSettingCard, IdentitySettingCard,
    LineEditSettingCard, PercentSpinBoxSettingCard, ProxySettingCard, SpinBoxSettingCard,
    addCardWidget,
)
from app.view.components.editors import FolderPicker, addRecentFolder


class SettingPage(QWidget):

    def __init__(self, featureService, browserService, browserListener, aria2RpcListener, coroutineRunner, categoryService, taskService, updateService, parent=None):
        super().__init__(parent)
        self._featureService = featureService
        self._browserService = browserService
        self._browserListener = browserListener
        self._aria2RpcListener = aria2RpcListener
        self._coroutineRunner = coroutineRunner
        self._categoryService = categoryService
        self._taskService = taskService
        self._updateService = updateService

        self.scrollArea = FastScrollArea(self)
        self.container = QWidget(self.scrollArea)
        self.vBoxLayout = QVBoxLayout(self.container)
        self.vBoxLayout.addStretch(1)
        self.groupNav = SettingGroupNav(self.scrollArea, self)
        self.hBoxLayout = QHBoxLayout(self)

        self.generalGroup = CollapsibleSettingCardGroup(self.tr('Download Settings'), "general", self.container)
        self.networkGroup = CollapsibleSettingCardGroup(self.tr('Network'), "network", self.container)
        self.browserGroup = CollapsibleSettingCardGroup(self.tr('Browser Extension'), "browser", self.container)
        self.aria2RpcGroup = CollapsibleSettingCardGroup(self.tr('Aria2 RPC Support'), "aria2rpc", self.container)
        self.personalGroup = CollapsibleSettingCardGroup(self.tr('Personalization'), "personalization", self.container)
        self.softwareGroup = CollapsibleSettingCardGroup(self.tr('Application'), "software", self.container)
        self.aboutGroup = CollapsibleSettingCardGroup(self.tr('About'), "about", self.container)

        from app.view.pages.task_page import EmptyStatusWidget
        self.emptyStatusWidget = EmptyStatusWidget(FluentIcon.SEARCH_MIRROR, self.tr('No matching settings found'), self)
        self.emptyStatusWidget.hide()

        self._initWidget()
        self._initCards()
        self._initLayout()
        self._bind()
        self._refreshBrowserStatus()
        self._refreshAria2Status()

    def addSettingGroup(self, group: CollapsibleSettingCardGroup) -> None:
        self.vBoxLayout.insertWidget(self.vBoxLayout.count() - 1, group)

    def _initWidget(self) -> None:
        self.setObjectName("SettingPage")
        self.scrollArea.setWidget(self.container)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.enableTransparentBackground()
        # 扣掉视口给滚动条让出的宽度，左右留白对称
        rightMargin = max(0, PAGE_MARGIN - self.scrollArea.viewportMargins().right())
        self.vBoxLayout.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, rightMargin, PAGE_MARGIN)

    def _initCards(self) -> None:
        from qfluentwidgets import SettingCard
        self.downloadFolderCard = SettingCard(FluentIcon.FOLDER, self.tr('Download Path'), self.tr('Default file save location'))
        self.downloadFolderPicker = FolderPicker(
            lambda: cfg.downloadFolder.defaultValue, self.tr('System Default'), self.downloadFolderCard
        )
        self.downloadFolderPicker.setPath(cfg.downloadFolder.value)
        addCardWidget(self.downloadFolderCard, self.downloadFolderPicker)

        self.categoryRulesCard = CategoryRulesCard(self._categoryService)

        self.speedLimitationCard = SpinBoxSettingCard(
            FluentIcon.SPEED_OFF, self.tr('Download Speed Limit'),
            self.tr('When Speed Limit is enabled at the Tasks page, combined speed of all tasks will be limited to this value'),
            suffix=" KB/s", configItem=cfg.speedLimitation,
            singleStep=512, division=1 / 1024,
        )

        self.generalGroup.addSettingCards([
            RangeSettingCard(cfg.maxTaskNum, FluentIcon.TRAIN, self.tr('Maximum Concurrent Tasks'),
                             self.tr('Maximum number of simultaneous transfers')),
            RangeSettingCard(cfg.preBlockNum, FluentIcon.CLOUD, self.tr('Pre-allocated Threads'),
                             self.tr('More threads speed up downloads\nOver 64 threads may trigger rate limiting and corrupt files')),
            SwitchSettingCard(FluentIcon.SPEED_HIGH, self.tr('Auto Boost'),
                              self.tr('Intelligently monitor thread efficiencies and automatically increase the number of threads to boost download speed'),
                              cfg.autoSpeedUp),
            SpinBoxSettingCard(FluentIcon.LIBRARY, self.tr('Minimum Redistribution Size'),
                               self.tr("If threads' workload exceeds this value, redistribution will trigger\nwhen a thread completes or Auto Boost is enabled"),
                               " KB", cfg.maxReassignSize, singleStep=64),
            self.speedLimitationCard,
            SwitchSettingCard(FluentIcon.HISTORY, self.tr('Preserve File Modification Timestamp'),
                              self.tr("Set file modification time to server's Last-Modified value after download"),
                              cfg.shouldPreserveLastModified),
            self.downloadFolderCard,
            self.categoryRulesCard,
            ComboBoxSettingCard(cfg.nameConflict, FluentIcon.COPY, self.tr('Duplicate Files'),
                                self.tr('How to handle duplicate file names in the download directory'),
                                texts=[self.tr('Keep Both'), self.tr('Overwrite'), self.tr('Ask')]),
            SwitchSettingCard(FluentIcon.BROOM, self.tr('Automatically Remove Tasks With Missing Content'),
                              self.tr('Automatically remove tasks whose contents are missing from the task list,\ncaused by file operations or possible disk disconnections'),
                              cfg.shouldRemoveMissingTasks),
            SwitchSettingCard(FluentIcon.ZIP_FOLDER, self.tr('Auto-Extract Archives'),
                              self.tr('Automatically extract .zip and .tar archives into a subfolder when completed'),
                              cfg.autoExtractArchives),
            SwitchSettingCard(FluentIcon.DELETE, self.tr('Delete Archive After Extraction'),
                              self.tr('Remove the original archive file after successful auto-extraction'),
                              cfg.deleteArchiveAfterExtract),
            SwitchSettingCard(FluentIcon.MOVIE, self.tr('Auto-Convert on Complete'),
                              self.tr('Automatically convert finished files (e.g. .mkv → .mp4, .webm → .mp3) using FFmpeg'),
                              cfg.autoConvertEnabled),
            SwitchSettingCard(FluentIcon.GLOBE, self.tr('Site-Specific Routing Rules'),
                              self.tr('Route downloads to subfolders and cap threads per domain (e.g. github.com → Code)'),
                              cfg.siteRulesEnabled),
            SwitchSettingCard(FluentIcon.DATE_TIME, self.tr('Scheduled Quiet Hours'),
                              self.tr('Automatically uncap download speed overnight and restore daytime limits'),
                              cfg.quietHoursEnabled),
        ])

        self.clientProfileCard = IdentitySettingCard()
        self.networkGroup.addSettingCards([
            ProxySettingCard(cfg.proxyServer, featureService=self._featureService),
            SwitchSettingCard(FluentIcon.CONNECT, self.tr('Use System DNS'),
                              self.tr('Use the system DNS resolver for better compatibility with TUN/VPN/Proxies'),
                              cfg.shouldUseSystemDns),
            SwitchSettingCard(FluentIcon.DEVELOPER_TOOLS, self.tr('Verify SSL Certificates'),
                              self.tr('Try disabling if files fail to download'),
                              cfg.shouldVerifySsl),
            self.clientProfileCard,
            HeadersPresetSettingCard(),
        ])

        self.browserEnableCard = SwitchSettingCard(
            FluentIcon.CONNECT, self.tr('Enable Browser Extension'),
            self.tr('Receive downloads from browser - extension installation required'),
            cfg.isBrowserExtensionEnabled,
        )

        self.chromiumInstallCard = PrimaryPushSettingCard(
            self.tr('Install'), FluentIcon.DOWNLOAD,
            self.tr('Install to Chromium Browser'),
            self.tr('Unpack extension and display installation guide (Chrome/Brave etc.); extension updates automatically with the desktop client'),
        )
        self.exportExtensionButton = HyperlinkButton(self.chromiumInstallCard)
        self.exportExtensionButton.setText(self.tr('Export CRX File'))
        addCardWidget(
            self.chromiumInstallCard, self.exportExtensionButton,
            before=self.chromiumInstallCard.button, spacing=16,
        )

        self.storeInstallCard = HyperlinkCard(
            FIREFOX_ADDONS_URL, self.tr('Firefox Store'), FluentIcon.GLOBE,
            self.tr('Install Extension From Web Stores'),
            self.tr('Store version updates may be delayed due to the review process'),
        )
        edgeBtn = HyperlinkButton(self.storeInstallCard)
        edgeBtn.setText(self.tr('Edge Store'))
        edgeBtn.setUrl(EDGE_ADDONS_URL)
        addCardWidget(self.storeInstallCard, edgeBtn, before=self.storeInstallCard.linkButton, spacing=16)

        chromeBtn = HyperlinkButton(self.storeInstallCard)
        chromeBtn.setText(self.tr('Chrome Store'))
        chromeBtn.setUrl(CHROME_WEBSTORE_URL)
        addCardWidget(self.storeInstallCard, chromeBtn, before=edgeBtn, spacing=16)

        self.browserPairTokenCard = PrimaryPushSettingCard(
            self.tr('Copy'), FluentIcon.COPY, self.tr('Pairing Token'),
            cfg.browserExtensionPairToken.value,
        )
        self.regenerateTokenButton = ToolButton(FluentIcon.SYNC, self.browserPairTokenCard)
        self.regenerateTokenButton.setToolTip(self.tr('Regenerate'))
        self.regenerateTokenButton.installEventFilter(ToolTipFilter(self.regenerateTokenButton))
        addCardWidget(self.browserPairTokenCard, self.regenerateTokenButton, spacing=8)

        self.browserAutoPortCard = SwitchSettingCard(
            FluentIcon.SYNC, self.tr('Automatically Select Port'),
            self.tr('Automatically switch to an available candidate port on port conflict'),
            cfg.shouldAutoSelectBrowserPort,
        )

        self.browserPortCard = SpinBoxSettingCard(
            FluentIcon.COMMAND_PROMPT, self.tr('Service Port'),
            self.tr('Port used for browser extension connection'),
            configItem=cfg.browserExtensionPort, singleStep=1, division=1,
        )
        self.browserPortCard.setEnabled(not cfg.shouldAutoSelectBrowserPort.value)

        browserCards = [self.browserEnableCard]
        if sys.platform != "darwin":
            self.urlSchemeCard = SwitchSettingCard(
                FluentIcon.LINK, self.tr('Allow Launching From Browser Extension'),
                self.tr('The browser extension may launch the app via dodown:// URL scheme'),
                cfg.isUrlSchemeRegistered,
            )
            browserCards.append(self.urlSchemeCard)
        browserCards.extend([
            SwitchSettingCard(FluentIcon.CHAT, self.tr('Create Draft When Intercepting Download'),
                              self.tr('Enter draft mode when automatically intercepting browser downloads to adjust download path and file name'),
                              cfg.shouldDraftTakenDownload),
            self.chromiumInstallCard,
            self.storeInstallCard,
            self.browserPairTokenCard,
            self.browserAutoPortCard,
            self.browserPortCard,
        ])
        self.browserGroup.addSettingCards(browserCards)

        self.aria2EnableCard = SwitchSettingCard(
            FluentIcon.LINK, self.tr('Enable Aria2 RPC Support'), self.tr('Enable support for the Aria2 JSON-RPC protocol, allow receiving download links from external tools'), cfg.isAria2RpcEnabled,
        )
        self.aria2RpcGroup.addSettingCards([
            self.aria2EnableCard,
            SpinBoxSettingCard(
                FluentIcon.GLOBE, self.tr('Port'),
                self.tr('Default Aria2 RPC port is 16800'),
                configItem=cfg.aria2RpcPort, singleStep=1, division=1,
            ),
            LineEditSettingCard(
                FluentIcon.FINGERPRINT, self.tr('Authentication Token'),
                self.tr('If set, clients must provide this token to create tasks'),
                configItem=cfg.aria2RpcToken,
                placeholder=self.tr('Optional'),
                isPassword=True,
            ),
            SwitchSettingCard(
                FluentIcon.VPN, self.tr('Spoof Browser Fingerprint'),
                self.tr('Attach Browser TLS Fingerprint and Request Headers to tasks received via Aria2 RPC'),
                cfg.aria2RpcEmulateFingerprint,
            ),
        ])

        self.zoomCard = PercentSpinBoxSettingCard(
            FluentIcon.ZOOM, self.tr('UI Scaling'),
            self.tr('Adjust UI scaling (0% for auto)'),
            configItem=cfg.dpiScale,
        )

        personalCards = [
            ComboBoxSettingCard(
                cfg.totoneThemePreset, FluentIcon.PALETTE, self.tr('Totone Studio Theme'),
                self.tr('Switch between 8 Totone studio color presets'),
                texts=[
                    "Totone Navy", "Midnight OLED", "Cybercore Lime", "Frutiger Aero",
                    "Sakura Dusk", "Studio Neutral", "Warm Film", "Paper Light",
                ],
            ),
            SwitchSettingCard(
                FluentIcon.PIN, self.tr('Floating Quick-Drop Pill'),
                self.tr('Keep a compact always-on-top drop target pill on your desktop'),
                cfg.showFloatingDropZone,
            ),
            ComboBoxSettingCard(cfg.themeMode, FluentIcon.BRUSH, self.tr('Application Theme'),
                                self.tr('Change application appearance'),
                                texts=[self.tr('Light'), self.tr('Dark'), self.tr('Follow System Settings')]),
        ]
        if sys.platform == "win32":
            personalCards.append(
                ComboBoxSettingCard(cfg.backgroundEffect, FluentIcon.TRANSPARENT,
                                    self.tr('Window Background Transparency Mode'),
                                    self.tr("Adjust transparency effects of windows' background"),
                                    texts=["Acrylic", "Mica", "MicaAlt", "Aero", "None"]),
            )
        elif sys.platform == "darwin":
            personalCards.append(
                ComboBoxSettingCard(cfg.backgroundEffect, FluentIcon.TRANSPARENT,
                                    self.tr('Window Background Transparency Mode'),
                                    self.tr("Adjust transparency effects of windows' background"),
                                    texts=["Acrylic", "None"]),
            )
        personalCards.append(self.zoomCard)
        if sys.platform == "darwin":
            self.showDockIconCard = SwitchSettingCard(
                FluentIcon.APPLICATION, self.tr('Show App Icon in Dock'),
                self.tr('If disabled, use the menu bar item to open this window'),
                cfg.shouldShowDockIcon,
            )
            self.showDockSpeedCard = SwitchSettingCard(
                FluentIcon.SPEED_HIGH, self.tr('Show Real-time Speed on Dock Icon'),
                self.tr('Overlay current download speed on Dock icon'),
                cfg.shouldShowDockSpeed,
            )
            self.showDockSpeedCard.setEnabled(cfg.shouldShowDockIcon.value)
            personalCards.extend([
                self.showDockIconCard,
                self.showDockSpeedCard,
                SwitchSettingCard(FluentIcon.SPEED_HIGH, self.tr('Show Real-time Speed in Menu Bar'),
                                  self.tr('Show current download speed next to menu bar icon'),
                                  cfg.shouldShowMenuBarSpeed),
            ])
        personalCards.append(
            ComboBoxSettingCard(cfg.language, FluentIcon.LANGUAGE, self.tr('Language'),
                                self.tr('Set the preferred language for the interface'),
                                texts=[self.tr('Use System Settings'), *map(toLanguageText, cfg.language.options[1:])]),
        )
        self.personalGroup.addSettingCards(personalCards)

        self.autoRunCard = SwitchSettingCard(
            FluentIcon.VPN, self.tr('Start on Boot'),
            self.tr('Start Dodown minimized on system startup'),
            cfg.shouldRunAtLogin,
        )
        from app.config.paths import APP_DATA_DIR, isPortable
        if isPortable():
            self.migrateCard = PushSettingCard(
                self.tr('Switch to User Mode'), FluentIcon.SYNC,
                self.tr('Configuration Data Storage Mode'),
                self.tr('Currently running in Portable mode, configuration stored next to the app:\n{0}').format(APP_DATA_DIR),
            )
        else:
            self.migrateCard = PushSettingCard(
                self.tr('Switch to Portable Mode'), FluentIcon.SYNC,
                self.tr('Configuration Data Storage Mode'),
                self.tr('Currently running in User mode, configuration stored at:\n{0}').format(APP_DATA_DIR),
            )

        self.taskPopupCard = ComboBoxSettingCard(
            cfg.taskPopupPlace, FluentIcon.SPEED_HIGH, self.tr('Download Progress for New Tasks'),
            self.tr('Choose how download progress for new tasks is shown'),
            texts=[self.tr('Hidden'), self.tr('Show in popup'), self.tr('Show in taskbar')],
        )
        self.taskPopupCard.setEnabled(cfg.noticeStyle.value == NoticeStyle.POPUP)

        self.commandLineToolCard = PushSettingCard(
            "", FluentIcon.COMMAND_PROMPT, self.tr('Command Line Tool'),
            self.tr('After installing, use the ghd command in a terminal to add and manage tasks'),
        )
        self._refreshCommandLineToolCard()

        softwareCards = [
            self.autoRunCard,
            ComboBoxSettingCard(
                cfg.closeMode, FluentIcon.POWER_BUTTON,
                self.tr('Main Window Closing Behavior'),
                self.tr('Choose whether to continue running in background or exit when closing the main window'),
                texts=[self.tr('Ask when closing'), self.tr('Continue running in background'), self.tr('Exit App')],
            ),
            ComboBoxSettingCard(
                cfg.noticeStyle, FluentIcon.RINGER, self.tr('Notification Style'),
                self.tr('How notices such as download complete or insufficient disk space are shown'),
                texts=[{NoticeStyle.POPUP: self.tr('Popup'), NoticeStyle.SYSTEM: self.tr('System notification'),
                        NoticeStyle.OFF: self.tr('Close')}[style] for style in cfg.noticeStyle.options],
            ),
            SwitchSettingCard(FluentIcon.VOLUME, self.tr('Notification Sound'),
                              self.tr('Play a sound on download completion'), cfg.isNoticeSoundEnabled),
            *([self.taskPopupCard] if NoticeStyle.POPUP in cfg.noticeStyle.options else []),
            ClipboardSettingCard(self._featureService.packs),
        ]
        if canShowPopup():
            self.clipboardAskCard = SwitchSettingCard(
                FluentIcon.CHAT, self.tr('Prompt on Link Copy'),
                self.tr('If enabled, when the main window is closed or minimized, show a popup prompting for download;\notherwise, open the main app window directly'),
                cfg.isClipboardRequestEnabled,
            )
            self.clipboardAskCard.setEnabled(cfg.isClipboardListenerEnabled.value)
            softwareCards.append(self.clipboardAskCard)
        if sys.platform != "darwin":
            self.associationCard = AssociationCard(self._featureService.packs)
            softwareCards.append(self.associationCard)
        softwareCards.extend([
            self.commandLineToolCard,
            self.migrateCard,
        ])
        self.softwareGroup.addSettingCards(softwareCards)

        self.feedbackCard = PrimaryPushSettingCard(
            self.tr('Provide Feedback'), FluentIcon.FEEDBACK,
            self.tr('Provide Feedback'),
            self.tr('Help improve Dodown by providing feedback,\nor view logs to troubleshoot issues'),
        )
        self.openLogButton = PushButton(self.tr('View Logs'), self.feedbackCard)
        addCardWidget(self.feedbackCard, self.openLogButton, spacing=8)

        self.packInfoCard = PrimaryPushSettingCard(
            self.tr('View Details'), FluentIcon.IOT, self.tr('Feature Packs'),
            self.tr('Manage currently installed feature packs'),
        )
        self.aboutCard = PrimaryPushSettingCard(
            self.tr('Check For Updates'), FluentIcon.INFO, self.tr('About'),
            f"© Copyright {YEAR}, {AUTHOR}. Version {VERSION}",
        )

        self.aboutGroup.addSettingCards([
            SwitchSettingCard(FluentIcon.UPDATE, self.tr('Check For Updates on Startup'),
                              self.tr('Get more features and improved stability with new versions'),
                              cfg.shouldCheckUpdateAtStartup),
            self.aboutCard,
            self.packInfoCard,
            self.feedbackCard,
            HyperlinkCard(AUTHOR_URL, self.tr("Open Author's Profile"), FluentIcon.PROJECTOR,
                          self.tr('About the Author'), self.tr('Discover more works by {}').format(AUTHOR)),
        ])

    def _initLayout(self) -> None:
        self.addSettingGroup(self.generalGroup)
        self.addSettingGroup(self.networkGroup)
        self.addSettingGroup(self.browserGroup)
        self.addSettingGroup(self.aria2RpcGroup)
        self.addSettingGroup(self.personalGroup)
        self.addSettingGroup(self.softwareGroup)
        for group in self._featureService.settingGroups(self.container):
            self.addSettingGroup(group)
        self.addSettingGroup(self.aboutGroup)

        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.addWidget(self.groupNav)
        self.hBoxLayout.addWidget(self.scrollArea, 1)
        self.groupNav.refresh()

    def _bind(self) -> None:
        cfg.appRestartSig.connect(self._showRestartTooltip)
        cfg.browserExtensionPairToken.valueChanged.connect(self._refreshPairTokenCard)
        cfg.shouldAutoSelectBrowserPort.valueChanged.connect(self._onAutoSelectPortChanged)
        self._browserService.connectionChanged.connect(self._refreshBrowserStatus, owner=self)
        self._browserListener.stateChanged.connect(self._refreshBrowserStatus, owner=self)
        self._aria2RpcListener.stateChanged.connect(self._refreshAria2Status, owner=self)
        if sys.platform == "darwin":
            cfg.shouldShowDockIcon.valueChanged.connect(self.showDockSpeedCard.setEnabled)
        cfg.noticeStyle.valueChanged.connect(self._onNoticeStyleChanged)
        if canShowPopup():
            cfg.isClipboardListenerEnabled.valueChanged.connect(self.clipboardAskCard.setEnabled)

        self.downloadFolderPicker.pathChanged.connect(self._onDownloadFolderChanged)
        cfg.downloadFolder.valueChanged.connect(self.downloadFolderPicker.setPath)

        self.browserPairTokenCard.clicked.connect(self._onCopyTokenClicked)
        self.regenerateTokenButton.clicked.connect(self._onRegenerateTokenClicked)
        self.chromiumInstallCard.clicked.connect(self._onChromiumInstallClicked)
        self.exportExtensionButton.clicked.connect(self._onExportExtensionClicked)
        if sys.platform != "darwin":
            self.urlSchemeCard.checkedChanged.connect(self._onUrlSchemeChanged)
        self.autoRunCard.checkedChanged.connect(self._onRunAtLoginChanged)
        self.commandLineToolCard.clicked.connect(self._onCommandLineToolClicked)
        self.packInfoCard.clicked.connect(self._onPackInfoClicked)
        self.aboutCard.clicked.connect(self._onAboutCardClicked)
        self.feedbackCard.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(FEEDBACK_URL)))
        self.openLogButton.clicked.connect(self._onOpenLogClicked)
        self.migrateCard.clicked.connect(self._onMigrateClicked)

    def _onNoticeStyleChanged(self, _value=None) -> None:
        self.taskPopupCard.setEnabled(cfg.noticeStyle.value == NoticeStyle.POPUP)

    def _onAutoSelectPortChanged(self, isAuto: bool) -> None:
        self.browserPortCard.setEnabled(not isAuto)

    def _onDownloadFolderChanged(self, path: str) -> None:
        cfg.set(cfg.downloadFolder, path)
        addRecentFolder(cfg.downloadFolder.value)

    def _showRestartTooltip(self) -> None:
        InfoBar.success(self.tr('Configuration Saved'), self.tr('Restart required to take effect'), duration=1500, parent=self)

    def _refreshPairTokenCard(self) -> None:
        self.browserPairTokenCard.setContent(cfg.browserExtensionPairToken.value)

    def _onCopyTokenClicked(self) -> None:
        token = cfg.browserExtensionPairToken.value
        QApplication.clipboard().setText(token)
        InfoBar.success(self.tr('Token Copied'), token,
                        duration=2000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

    def _onRegenerateTokenClicked(self) -> None:
        token = self._browserService.regenerateToken()
        QApplication.clipboard().setText(token)
        InfoBar.success(self.tr('Token Regenerated'), self.tr('Copied new token to clipboard'),
                        duration=2000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

    def _onChromiumInstallClicked(self) -> None:
        self._coroutineRunner.submit(
            self._browserService.install(),
            done=self._onExtensionExtractDone,
            failed=self._onExtensionExtractFailed,
        )

    def _onExtensionExtractDone(self, path) -> None:
        from app.view.dialogs.extension_install import ExtensionInstallDialog
        ExtensionInstallDialog(path, self.window()).exec()

    def _onExtensionExtractFailed(self, error) -> None:
        InfoBar.error(self.tr('Unpack failed'), toLocalizedError(toTaskError(error)),
                      duration=3000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

    def _refreshBrowserStatus(self, *_) -> None:
        state = self._browserListener.state
        installType, version = self._browserService.connectionSummary
        if state.status == ListenStatus.OFF:
            text = self.tr('Receive downloads from browser - extension installation required')
        elif state.status == ListenStatus.FAILED:
            text = toLocalizedError(state.error)
        elif not installType:
            text = self.tr('Not Connected')
        elif installType == "development":
            text = self.tr('Connected v{} (Desktop-managed)').format(version)
        else:
            text = self.tr('Connected v{} (Store-installed)').format(version)
        self.browserEnableCard.setContent(text)

    def _refreshAria2Status(self, *_) -> None:
        state = self._aria2RpcListener.state
        if state.status == ListenStatus.OFF:
            text = self.tr('Enable support for the Aria2 JSON-RPC protocol, allow receiving download links from external tools')
        elif state.status == ListenStatus.FAILED:
            text = toLocalizedError(state.error)
        else:
            text = self.tr('Listening on port {}').format(state.port)
        self.aria2EnableCard.setContent(text)

    def _onExportExtensionClicked(self) -> None:
        from PySide6.QtCore import QFile, QIODevice
        from PySide6.QtWidgets import QFileDialog
        from app.platform.desktop import loadCrx
        path, _ = QFileDialog.getSaveFileName(self, self.tr('Select Export Path'),
                                              "./Extension.crx", "Chromium Extension(*.crx)")
        if path:
            f = QFile(path)
            if f.open(QIODevice.OpenModeFlag.WriteOnly):
                f.write(loadCrx())
                f.close()

    def _onUrlSchemeChanged(self, enabled: bool) -> None:
        from app.platform.file_association import registerUrlScheme, unregisterUrlScheme
        if enabled:
            registerUrlScheme()
        else:
            unregisterUrlScheme()

    def _onRunAtLoginChanged(self, enabled: bool) -> None:
        from app.platform.run_at_login import setRunAtLogin
        setRunAtLogin(enabled)

    def _refreshCommandLineToolCard(self) -> None:
        from app.platform import cli_install
        self.commandLineToolCard.button.setEnabled(True)
        self.commandLineToolCard.button.setText(
            self.tr('Uninstall') if cli_install.isInstalled() else self.tr('Install'))

    def _onCommandLineToolClicked(self) -> None:
        from app.platform import cli_install
        work = cli_install.delete() if cli_install.isInstalled() else cli_install.install()
        self.commandLineToolCard.button.setEnabled(False)
        self._coroutineRunner.submit(work, done=self._onCommandLineToolDone, failed=self._onCommandLineToolFailed)

    def _onCommandLineToolDone(self, _) -> None:
        from app.platform import cli_install
        self._refreshCommandLineToolCard()
        if not cli_install.isInstalled():
            InfoBar.success(self.tr('Command line tool uninstalled'), "", duration=2000,
                            position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())
            return
        content = self.tr('ghd is available in newly opened terminals')
        if sys.platform == "linux":
            content = self.tr('ghd is available in newly opened terminals; if the command is not found, add ~/.local/bin to PATH')
        InfoBar.success(self.tr('Command line tool installed'), content, duration=5000,
                        position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

    def _onCommandLineToolFailed(self, error) -> None:
        from app.platform import cli_install
        self._refreshCommandLineToolCard()
        title = self.tr('Failed to uninstall command line tool') if cli_install.isInstalled() else self.tr('Failed to install command line tool')
        InfoBar.error(title, toLocalizedError(toTaskError(error)),
                      duration=5000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

    def _onMigrateClicked(self) -> None:
        from app.config.paths import isPortable, migrate, PORTABLE_DIR, USER_DATA_DIR

        target = USER_DATA_DIR if isPortable() else PORTABLE_DIR
        mode = self.tr('User Mode') if isPortable() else self.tr('Portable Mode')
        dialog = MessageBox(
            self.tr('Switch Data Storage Mode'),
            self.tr('Are you sure you want to switch to {0}?\n\nData will be copied to new location and the app will then exit. Please manually launch the app again.').format(mode),
            self.window(),
        )
        isConfirmed = dialog.exec()
        dialog.deleteLater()
        if not isConfirmed:
            return

        QApplication.instance().aboutToQuit.connect(lambda: migrate(target))
        QApplication.instance().quit()

    def _onPackInfoClicked(self) -> None:
        from app.view.dialogs.pack_info import PackInfoDialog
        dialog = PackInfoDialog(self._featureService.packs, self._updateService, self.window())
        dialog.exec()
        dialog.deleteLater()

    def _onAboutCardClicked(self) -> None:
        from app.services.update_service import UpdateState

        InfoBar.info(self.tr('Check For Updates'), self.tr('Checking for updates...'),
                     duration=1500, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

        def onChecked(info):
            if info.targetId != "app" or info.state not in (UpdateState.AVAILABLE, UpdateState.IDLE):
                return
            self._updateService.changed.disconnect(onChecked)
            if info.state == UpdateState.IDLE:
                if info.error is not None:
                    InfoBar.error(self.tr('Failed to check update'), self.tr('Unable to get the latest version information'),
                                  duration=3000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())
                else:
                    InfoBar.success(self.tr("You're running the latest version"), "",
                                    duration=3000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

        self._updateService.changed.connect(onChecked, owner=self)
        self._updateService.check()

    def _onOpenLogClicked(self) -> None:
        from app.config.paths import APP_DATA_DIR
        from app.platform.desktop import revealInFolder
        revealInFolder(f"{APP_DATA_DIR}/Dodown.log")

    @property
    def searchPlaceholder(self) -> str:
        return self.tr('Search Settings')

    def setSearchText(self, text: str) -> None:
        hasMatch = False
        for group in groupsIn(self.vBoxLayout):
            group.setSearchText(text)
            hasMatch = hasMatch or not group.isHidden()

        self.emptyStatusWidget.setVisible(not hasMatch)
        if not hasMatch:
            self.emptyStatusWidget.adjustSize()
            self._refreshEmptyWidgetGeometry()
        self.groupNav.refresh()

    def _refreshEmptyWidgetGeometry(self) -> None:
        navWidth = self.groupNav.width()
        self.emptyStatusWidget.move(
            navWidth + (self.width() - navWidth - self.emptyStatusWidget.width()) // 2,
            (self.height() - self.emptyStatusWidget.height()) // 2,
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.emptyStatusWidget.isVisible():
            self._refreshEmptyWidgetGeometry()

    def showEvent(self, event) -> None:
        restoreGroupOrder(self.vBoxLayout, self.aboutGroup.objectName())
        self.groupNav.refresh()
        super().showEvent(event)
