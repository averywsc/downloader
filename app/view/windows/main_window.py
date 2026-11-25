from __future__ import annotations

import sys
from collections.abc import Callable
from functools import cached_property
from typing import TYPE_CHECKING

from PySide6.QtCore import QCoreApplication, QEvent, QRect, QUrl, QTimer, Qt
from PySide6.QtGui import QColor, QIcon, QDesktopServices, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    MSFluentWindow, FluentIcon, NavigationItemPosition, MessageBox, Theme, InfoBar, InfoBarIcon, InfoBarPosition,
    SearchLineEdit, IconWidget, SubtitleLabel, isDarkTheme, CheckBox, PrimaryPushButton,
    PushButton, ToolTipFilter, TransparentToolButton, qconfig,
)
from qfluentwidgets.common import qrouter
from qfluentwidgets.common.style_sheet import updateStyleSheet
from qfluentwidgets.components.dialog_box.mask_dialog_base import MaskDialogBase

from app.config.cfg import CloseMode, cfg
from app.config.constants import DONATE_URL, FEEDBACK_URL
from app.config.paths import APP_DATA_DIR
from app.platform.desktop import raiseWindow, revealInFolder
from app.services.task_draft import TaskDraft
from app.i18n import toLocalizedError
from app.models.task import TaskError, TaskOptions, TaskStatus
from app.services.port_listener import PortListener
from app.signal_bus import signalBus
from app.services.update_service import UpdateState
from app.view.components.labels import IconBodyLabel
from app.view.components.totone_status_bar import TotoneStatusBar
from app.view.pages.task_page import TaskPage
from app.view.totone_theme import (
    TOTONE_ACC, TOTONE_BG, TOTONE_EDGE, TOTONE_PANEL, TOTONE_THEME_NAMES,
    applyTotoneTheme, currentPalette, dodownIcon, styleWindowTotone,
)
from app.services.power_tools import PowerToolsService

if sys.platform == "darwin":
    import Cocoa
    from qframelesswindow.mac import MacFramelessWindowBase
    from qframelesswindow.utils.mac_utils import getNSWindow

if TYPE_CHECKING:
    from qfluentwidgets import FluentIconBase
    from app.models.task import Task
    from app.services.browser_service import BrowserService, PairRequest
    from app.services.category_service import CategoryService
    from app.services.coroutine_runner import CoroutineRunner
    from app.services.plan import Plan
    from app.services.speed_meter import SpeedMeter
    from app.services.feature_service import FeatureService
    from app.services.task_service import TaskService
    from app.services.update_service import UpdateInfo, UpdateService
    from app.view.dialogs.task_draft import TaskDraftDialog


class DropOverlay(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initWidget()
        self._initLayout()

    def _initWidget(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._icon = IconWidget(FluentIcon.FOLDER_ADD, self)
        self._icon.setFixedSize(48, 48)
        self._icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._label = SubtitleLabel(self.tr('Drop to add task'), self)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.hide()

    def _initLayout(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(8)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(5, 12, 31, 200))
        pen = QPen(QColor(TOTONE_ACC), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(14, 14, -14, -14), 6, 6)


class MainWindow(MSFluentWindow):

    def __init__(
        self,
        taskService: TaskService,
        featureService: FeatureService,
        browserService: BrowserService,
        browserListener: PortListener,
        aria2RpcListener: PortListener,
        categoryService: CategoryService,
        speedMeter: SpeedMeter,
        coroutineRunner: CoroutineRunner,
        plan: Plan,
        updateService: UpdateService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        self._isGeometryRestored = False
        self._isBackgroundEffectDirty = False
        self._macVisualEffectView = None
        self.searchEdit = None
        self._dropOverlay = None
        super().__init__(parent)
        self._taskService = taskService
        self._featureService = featureService
        self._browserService = browserService
        self._browserListener = browserListener
        self._aria2RpcListener = aria2RpcListener
        self._categoryService = categoryService
        self._coroutineRunner = coroutineRunner
        self._speedMeter = speedMeter
        self._updateService = updateService
        self._plan = plan
        self.setMicaEffectEnabled(False)
        if sys.platform != "darwin":
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._pages: dict[str, QWidget] = {}
        self._progressToast = None
        self._draft = TaskDraft(self._coroutineRunner, self._featureService, self._taskService.add)
        self.searchEdit = SearchLineEdit(self.titleBar)

        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        styleWindowTotone(self)
        self.setWindowIcon(dodownIcon())
        self.setWindowTitle('Dodown')
        self.setMinimumSize(960, 540)
        if hasattr(self.titleBar, "titleLabel"):
            self.titleBar.titleLabel.setObjectName("totoneBrandTitle")
        if sys.platform == "darwin" and cfg.backgroundEffect.value != "None":
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.titleBar.hBoxLayout.insertSpacing(2, 6)
        if sys.platform == "darwin":
            self.titleBar.hBoxLayout.insertSpacing(0, 60)

        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.hide()
        self.searchEdit.raise_()

        self.setAcceptDrops(True)
        self._dropOverlay = DropOverlay(self)

        self._powerTools = PowerToolsService(self._taskService, parent=self)
        self.totoneStatusBar = TotoneStatusBar(self._taskService, self._speedMeter, parent=self)
        self._floatingDrop = None
        if hasattr(self, "hBoxLayout"):
            m = self.hBoxLayout.contentsMargins()
            self.hBoxLayout.setContentsMargins(m.left(), m.top(), m.right(), 30)

    def _initLayout(self) -> None:
        self.navigationInterface.addItem(
            routeKey="TaskPage", icon=FluentIcon.DOWNLOAD, text=self.tr('Tasks'),
            onClick=self.showTasks, position=NavigationItemPosition.TOP,
        )
        self.navigationInterface.addItem(
            routeKey="addTaskButton", icon=FluentIcon.ADD, text=self.tr('New Task'),
            selectable=False, onClick=lambda: self.addUrls([]), position=NavigationItemPosition.TOP,
        )
        self.navigationInterface.addItem(
            routeKey="mediaStudioButton", icon=FluentIcon.VIDEO, text=self.tr('Media'),
            selectable=False, onClick=self.openMediaStudio, position=NavigationItemPosition.TOP,
        )
        self.navigationInterface.addItem(
            routeKey="batchUrlButton", icon=FluentIcon.ADD_TO, text=self.tr('Batch'),
            selectable=False, onClick=self.openBatchUrlDialog, position=NavigationItemPosition.TOP,
        )
        self.navigationInterface.addItem(
            routeKey="hashCheckButton", icon=FluentIcon.FINGERPRINT, text=self.tr('Verify'),
            selectable=False, onClick=self.openHashChecker, position=NavigationItemPosition.BOTTOM,
        )
        self.navigationInterface.addItem(
            routeKey="automationButton", icon=FluentIcon.DATE_TIME, text=self.tr('Rules'),
            selectable=False, onClick=self.openAutomationRules, position=NavigationItemPosition.BOTTOM,
        )
        self.navigationInterface.addItem(
            routeKey="SettingPage", icon=FluentIcon.SETTING, text=self.tr('Settings'),
            onClick=self.showSettings, position=NavigationItemPosition.BOTTOM,
        )
        self.showTasks()

    def setupPacks(self) -> None:
        for PageClass in self._featureService.pages():
            routeKey = PageClass.__name__
            self.navigationInterface.addItem(
                routeKey=routeKey, icon=PageClass.icon,
                text=QCoreApplication.translate("PackPage", PageClass.title),
                onClick=lambda cls=PageClass, key=routeKey: self._showPage(
                    key, lambda: self._featureService.createPage(cls, parent=self),
                ),
                position=NavigationItemPosition.TOP,
            )

    def showTasks(self) -> None:
        self._showPage("TaskPage", lambda: TaskPage(
            self._taskService, self._featureService,
            self._categoryService, self._speedMeter, self._plan, parent=self,
        ))

    def showSettings(self) -> None:
        from app.view.pages.setting_page import SettingPage
        self._showPage("SettingPage", lambda: SettingPage(
            self._featureService, self._browserService, self._browserListener, self._aria2RpcListener,
            self._coroutineRunner, self._categoryService, self._taskService,
            self._updateService, parent=self,
        ))

    def systemTitleBarRect(self, size) -> QRect:
        return QRect(0, 10, 75, size.height())

    def _normalBackgroundColor(self):
        if sys.platform == "darwin" and cfg.backgroundEffect.value != "None":
            return QColor(5, 12, 31, 180)
        if self.styleSheet() == "":
            return QColor(TOTONE_BG)
        return QColor(0, 0, 0, 0)

    def _showPage(self, routeKey: str, createPage: Callable[[], QWidget]) -> None:
        page = self._pages.get(routeKey)
        if page is None:
            page = createPage()
            page.setObjectName(routeKey)
            # addSubInterface 会设这个属性，懒创建绕过了它；不设时每次切页都会重刷整个内容区的样式
            page.setProperty("isStackedTransparent", False)
            self.stackedWidget.addWidget(page)
            self._pages[routeKey] = page
            if self.stackedWidget.count() == 1:
                self.stackedWidget.currentChanged.connect(self._onCurrentInterfaceChanged)
                qrouter.setDefaultRouteKey(self.stackedWidget, routeKey)
        self.switchTo(page)
        self.navigationInterface.setCurrentItem(routeKey)
        self._updateSearchTarget(page)

    def _onSearchTextChanged(self, text: str) -> None:
        page = self.stackedWidget.currentWidget()
        if hasattr(page, 'setSearchText'):
            page.setSearchText(text)

    def _updateSearchTarget(self, page: QWidget) -> None:
        self.searchEdit.clear()
        if hasattr(page, 'searchPlaceholder'):
            self.searchEdit.setPlaceholderText(page.searchPlaceholder)
            self.searchEdit.show()
        else:
            self.searchEdit.hide()

    def _refreshSearchEditGeometry(self) -> None:
        tb = self.titleBar
        w = min(360, tb.width() - 300)
        w = max(200, w)
        self.searchEdit.setFixedWidth(w)
        x = (tb.width() - w) // 2
        y = (tb.height() - self.searchEdit.height()) // 2
        self.searchEdit.move(x, y)

    def _onSearchShortcut(self) -> None:
        if self.searchEdit.isVisible():
            self.searchEdit.setFocus()
            self.searchEdit.selectAll()

    def _bind(self) -> None:
        self._draft.addFailed.connect(self.addTasks, owner=self)
        self._draft.parseFailed.connect(self._onDraftParseFailed, owner=self)
        cfg.themeChanged.connect(self._setTheme)
        QApplication.instance().styleHints().colorSchemeChanged.connect(self._onSystemColorSchemeChanged)
        self.titleBar.closeBtn.clicked.disconnect(self.close)
        self.titleBar.closeBtn.clicked.connect(self._onCloseClicked)
        self.searchEdit.textChanged.connect(self._onSearchTextChanged)

        QShortcut(QKeySequence.StandardKey.Find, self).activated.connect(self._onSearchShortcut)
        QShortcut(QKeySequence("Ctrl+K"), self).activated.connect(self.openCommandPalette)

        self.totoneStatusBar.commandPaletteRequested.connect(self.openCommandPalette)
        self.totoneStatusBar.dropWidgetToggled.connect(self.setFloatingDropVisible)
        cfg.showFloatingDropZone.valueChanged.connect(self.setFloatingDropVisible)
        cfg.totoneThemePreset.valueChanged.connect(self._applyTotonePreset)
        self._powerTools.noticeRequested.connect(self._onPowerNotice)
        self._powerTools.quietHoursStateChanged.connect(self.totoneStatusBar.setQuietHoursActive)
        if cfg.showFloatingDropZone.value:
            self.setFloatingDropVisible(True)

        if self._updateService is not None:
            self._updateService.changed.connect(self._onUpdateChanged, owner=self)

        if sys.platform == "win32":
            cfg.backgroundEffect.valueChanged.connect(self._setBackgroundEffectWin)
            self._speedMeter.speedChanged.connect(self._onSpeedChanged, owner=self)
        elif sys.platform == "darwin":
            cfg.backgroundEffect.valueChanged.connect(self._setBackgroundEffectMac)
            QShortcut(QKeySequence.StandardKey.Close, self).activated.connect(self._onCloseClicked)


    def addUrls(self, urls: list[str]) -> None:
        dialog = self._draftDialog
        if urls:
            dialog.addUrls(urls)
        if not dialog.isVisible():
            dialog.showMask()

    def addTasks(self, tasks: list[Task], error: TaskError | None = None) -> None:
        self._draftDialog.addParsedTasks(tasks, error)
        self._openDraftDialog()

    def _onDraftParseFailed(self, url: str, error: TaskError) -> None:
        self._openDraftDialog()

    def _openDraftDialog(self) -> None:
        dialog = self._draftDialog
        if dialog.isActive:
            return
        if sys.platform == "darwin":
            self.show()
            raiseWindow(self)
            dialog.showMask()
        else:
            dialog.showStandalone()

    def _add(self, task: Task) -> None:
        try:
            self._taskService.add(task)
        except TaskError as e:
            self.addTasks([task], e)

    @cached_property
    def _draftDialog(self) -> TaskDraftDialog:
        from app.view.dialogs.task_draft import TaskDraftDialog
        return TaskDraftDialog(
            self._draft, self._featureService, self._categoryService,
            parent=self,
        )

    def onPairRequested(self, request: PairRequest) -> None:
        content = self.tr(
            'A browser extension is requesting to pair with Dodown.\n\nFrom: {0}\nClient: {1}\nExtension Version: {2}\n\nOnly allow this request if you have requested "Auto Pair" from the extension.'
        ).format(request.peerAddress, request.clientKind or self.tr('Browser Extension'),
                 request.extensionVersion or self.tr('Unknown'))

        dialog = MessageBox(self.tr('Browser Extension Pairing Request'), content, self)
        dialog.yesButton.setText(self.tr('Allow'))
        dialog.cancelButton.setText(self.tr('Decline'))
        dialog.contentLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if dialog.exec():
            self._browserService.approvePair(request.requestId)
        else:
            self._browserService.rejectPair(request.requestId)
        dialog.deleteLater()

    def onBrowserListenFailed(self, error: TaskError) -> None:
        self._onListenFailed(self.tr('Unable to start browser extension service'), error)

    def onAria2ListenFailed(self, error: TaskError) -> None:
        self._onListenFailed(self.tr('Unable to start Aria2 RPC service'), error)

    def _onListenFailed(self, title: str, error: TaskError) -> None:
        infoBar = InfoBar(
            icon=InfoBarIcon.ERROR,
            title=title,
            content=toLocalizedError(error),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            duration=-1,
            position=InfoBarPosition.BOTTOM_RIGHT,
            parent=self,
        )
        settingButton = PushButton(FluentIcon.SETTING, self.tr('Open Settings'))
        settingButton.clicked.connect(lambda: (infoBar.close(), self.showSettings()))
        infoBar.addWidget(settingButton)
        infoBar.show()

    def onUpdateAvailable(self, info) -> None:
        if self._progressToast is not None:
            self._progressToast.deleteLater()
            self._progressToast = None

        infoBar = InfoBar(
            icon=FluentIcon.CLOUD,
            title=self.tr('New Version Available'),
            content=self.tr('Latest version: {0}').format(info.latestVersion),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            duration=-1,
            position=InfoBarPosition.BOTTOM_RIGHT,
            parent=self,
        )
        downloadButton = PrimaryPushButton(FluentIcon.DOWNLOAD, self.tr('Download Now'))
        if self._updateService.canSelfUpdate():
            downloadButton.clicked.connect(lambda: (infoBar.close(), self._updateService.download("app")))
        else:
            downloadButton.clicked.connect(lambda: (infoBar.close(), self._downloadBestAsset()))
        infoBar.addWidget(downloadButton)
        detailButton = PushButton(FluentIcon.CHAT, self.tr('View Details'))
        detailButton.clicked.connect(self._showReleaseDetails)
        infoBar.addWidget(detailButton)
        sponsorButton = PushButton(FluentIcon.HEART, self.tr('Buy Author A Coffee'))
        sponsorButton.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATE_URL)))
        infoBar.addWidget(sponsorButton)
        infoBar.show()

    def _downloadBestAsset(self) -> None:
        from app.update import fetchBestAssetUrl

        def onUrl(url):
            if url is None:
                self._showReleaseDetails()
                return
            self._coroutineRunner.submit(
                self._featureService.parse(TaskOptions(url=url)),
                done=self._add,
                owner=self,
            )

        self._coroutineRunner.submit(fetchBestAssetUrl(), done=onUrl, owner=self)

    def _onUpdateChanged(self, info) -> None:
        if info.targetId != "app":
            return
        if info.state not in (UpdateState.DOWNLOADING, UpdateState.READY, UpdateState.FAILED):
            return
        if self._progressToast is None:
            from app.view.components.progress_toast import ProgressToast
            self._progressToast = ProgressToast(
                onRetry=lambda: self._updateService.download("app"),
                parent=self,
            )
        self._progressToast.setInfo(info)

    def _showReleaseDetails(self) -> None:
        from app.update import fetchAssetUrl, fetchRelease
        from app.view.dialogs.release_info import ReleaseInfoDialog

        def onFetched(release):
            dialog = ReleaseInfoDialog(release, self)

            def onAccepted():
                asset = dialog.selectedAsset()
                if asset is None:
                    return

                def onUrl(url):
                    self._coroutineRunner.submit(
                        self._featureService.parse(TaskOptions(url=url)),
                        done=self._add,
                        owner=self,
                    )

                self._coroutineRunner.submit(
                    fetchAssetUrl(release.version, asset.name),
                    done=onUrl, owner=self,
                )

            dialog.accepted.connect(onAccepted)
            dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            dialog.show()

        self._coroutineRunner.submit(fetchRelease(), done=onFetched, owner=self)

    def onExceptionCaught(self, message: str) -> None:
        dialog = MessageBox(
            self.tr('An exception occurred'),
            self.tr('After clicking "OK", the error info will be copied and the feedback page will open.\n\n{0}').format(message),
            self,
        )
        logButton = TransparentToolButton(FluentIcon.DOCUMENT, dialog)
        logButton.setToolTip(self.tr('View Logs'))
        logButton.installEventFilter(ToolTipFilter(logButton))
        logButton.clicked.connect(self._openLogFolder)

        dialog.contentLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        titleLayout = dialog.textLayout
        titleLayout.removeWidget(dialog.titleLabel)
        titleRow = QHBoxLayout()
        titleRow.addWidget(dialog.titleLabel, 1)
        titleRow.addWidget(logButton)
        titleLayout.insertLayout(0, titleRow)

        if dialog.exec():
            QApplication.clipboard().setText(message)
            QDesktopServices.openUrl(QUrl(FEEDBACK_URL))
        dialog.deleteLater()

    def _openLogFolder(self) -> None:
        revealInFolder(f"{APP_DATA_DIR}/Dodown.log")

    def _onSpeedChanged(self, _speed: int) -> None:
        from app.platform.taskbar import setWindowsProgress
        status = TaskStatus.RUNNING if self._taskService.runningCount() > 0 else None
        setWindowsProgress(int(self.winId()), status, self._taskService.overallProgress())

    def _onCloseClicked(self) -> None:
        for dialog in self.findChildren(MaskDialogBase):
            if dialog.isVisible():
                dialog.reject()
                return
        if sys.platform == "darwin" and self.isFullScreen():
            self.showNormal()
            QTimer.singleShot(1000, self._onCloseClicked)
            return

        mode = cfg.closeMode.value

        if sys.platform == "darwin" and mode != CloseMode.QUIT:
            if not self.isMaximized():
                geo = self.geometry()
                cfg.set(cfg.geometry, (geo.x(), geo.y(), geo.width(), geo.height()))
            self.hide()
            return

        if mode == CloseMode.ASK:
            dialog = MessageBox(
                self.tr('Exit App Completely?'),
                self.tr('While running in background, you may reopen the app from the system tray icon.'),
                self,
            )
            dialog.yesButton.setText(self.tr('Exit App'))
            dialog.cancelButton.setText(self.tr('Continue running in background'))
            checkbox = CheckBox(self.tr('Remember my choice'), dialog)
            dialog.textLayout.addWidget(checkbox)
            mode = CloseMode.QUIT if dialog.exec() else CloseMode.BACKGROUND
            if checkbox.isChecked():
                cfg.set(cfg.closeMode, mode)
            dialog.deleteLater()

        self.close()
        if mode == CloseMode.QUIT:
            QApplication.quit()

    def dragEnterEvent(self, event) -> None:
        if QApplication.instance().isFileDragActive:
            event.ignore()
            return
        mime = event.mimeData()
        acceptable = mime.hasUrls() or (
            mime.hasText() and any(
                self._featureService.match(line.strip())
                for line in mime.text().splitlines() if line.strip()))
        if not acceptable:
            event.ignore()
            return
        if any(d.isVisible() for d in self.findChildren(MaskDialogBase)):
            event.ignore()
            return
        event.acceptProposedAction()
        self._dropOverlay.setGeometry(self.rect())
        self._dropOverlay.show()
        self._dropOverlay.raise_()

    def dragMoveEvent(self, event) -> None:
        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._dropOverlay.hide()

    def dropEvent(self, event) -> None:
        self._dropOverlay.hide()
        mime = event.mimeData()
        if mime.hasUrls():
            urls = [u.toString() for u in mime.urls()]
        else:
            urls = [line.strip() for line in mime.text().splitlines()
                    if line.strip() and self._featureService.match(line.strip())]
        if urls:
            self.addUrls(urls)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "totoneStatusBar") and self.totoneStatusBar is not None:
            h = self.totoneStatusBar.height()
            self.totoneStatusBar.setGeometry(0, self.height() - h, self.width(), h)
            self.totoneStatusBar.raise_()
        if self._dropOverlay is not None and self._dropOverlay.isVisible():
            self._dropOverlay.setGeometry(self.rect())
        if self.searchEdit is not None and self.searchEdit.isVisible():
            self._refreshSearchEditGeometry()

    def _applyTotonePreset(self, presetName: str) -> None:
        app = QApplication.instance()
        if app is not None:
            applyTotoneTheme(app, presetName)
        styleWindowTotone(self, presetName)
        if hasattr(self, "totoneStatusBar"):
            self.totoneStatusBar.refreshTheme()
        if self._floatingDrop is not None:
            self._floatingDrop.update()
        self.update()

    def _onPowerNotice(self, level: str, title: str, content: str) -> None:
        fn = {
            "success": InfoBar.success,
            "warning": InfoBar.warning,
            "error": InfoBar.error,
        }.get(level, InfoBar.info)
        fn(title, content, duration=4500, position=InfoBarPosition.BOTTOM_RIGHT, parent=self)

    def setFloatingDropVisible(self, visible: bool) -> None:
        if visible:
            if self._floatingDrop is None:
                from app.view.shell.drop_widget import FloatingDropWidget
                self._floatingDrop = FloatingDropWidget(self._speedMeter, self._taskService)
                self._floatingDrop.urlsDropped.connect(self.addUrls)
                self._floatingDrop.activateRequested.connect(lambda: (self.show(), raiseWindow(self)))
            self._floatingDrop.show()
            self._floatingDrop.raise_()
        elif self._floatingDrop is not None:
            self._floatingDrop.hide()

    def openMediaStudio(self) -> None:
        from app.view.dialogs.power_dialogs import MediaStudioDialog
        dlg = MediaStudioDialog(onQueueUrls=self.addUrls, parent=self)
        dlg.exec()
        dlg.deleteLater()

    def openBatchUrlDialog(self) -> None:
        from app.view.dialogs.batch_url import BatchUrlDialog
        dlg = BatchUrlDialog(self)
        if dlg.exec() and dlg.urls():
            self.addUrls(dlg.urls())
        dlg.deleteLater()

    def openHashChecker(self) -> None:
        from app.view.dialogs.power_dialogs import HashCheckerDialog
        dlg = HashCheckerDialog(self._powerTools, parent=self)
        dlg.exec()
        dlg.deleteLater()

    def openAutomationRules(self) -> None:
        from app.view.dialogs.power_dialogs import AutomationRulesDialog
        dlg = AutomationRulesDialog(self)
        dlg.exec()
        dlg.deleteLater()

    def openCommandPalette(self) -> None:
        from app.view.dialogs.command_palette import CommandPaletteDialog, PaletteAction

        actions: list[PaletteAction] = [
            PaletteAction("New Download Task", "TASK", lambda: self.addUrls([]), "add url link"),
            PaletteAction("Media & Playlist Studio (MP4 / MP3 / FLAC / WAV / Clip)", "MEDIA", self.openMediaStudio, "yt-dlp youtube audio clip"),
            PaletteAction("Batch URL Range Generator ([01-12])", "TASK", self.openBatchUrlDialog, "range template series"),
            PaletteAction("Hash & VirusTotal Verifier", "TOOLS", self.openHashChecker, "sha256 md5 checksum security"),
            PaletteAction("Automation, Site Rules & Quiet Hours", "RULES", self.openAutomationRules, "schedule convert extract"),
            PaletteAction("Start All Tasks", "QUEUE", lambda: self._taskService.startAll(), "resume play"),
            PaletteAction("Pause All Tasks", "QUEUE", lambda: self._taskService.pauseAll(), "stop"),
            PaletteAction(
                "Toggle Speed Limit", "SPEED",
                lambda: cfg.set(cfg.isSpeedLimitEnabled, not cfg.isSpeedLimitEnabled.value),
                "throttle cap bandwidth",
            ),
            PaletteAction(
                "Toggle Floating Drop Pill", "UI",
                lambda: cfg.set(cfg.showFloatingDropZone, not cfg.showFloatingDropZone.value),
                "mini widget drag drop",
            ),
            PaletteAction(
                "Toggle Auto-Extract Archives", "AUTOMATION",
                lambda: cfg.set(cfg.autoExtractArchives, not cfg.autoExtractArchives.value),
                "unzip zip tar",
            ),
            PaletteAction(
                "Toggle Auto-Convert on Complete", "AUTOMATION",
                lambda: cfg.set(cfg.autoConvertEnabled, not cfg.autoConvertEnabled.value),
                "ffmpeg mkv mp4 mp3",
            ),
            PaletteAction("Open Downloads Folder", "FILES", lambda: revealInFolder(str(cfg.downloadFolder.value)), "explorer finder"),
            PaletteAction("Go to Tasks", "NAV", self.showTasks, "downloads list"),
            PaletteAction("Go to Settings", "NAV", self.showSettings, "preferences config"),
        ]
        for themeName in TOTONE_THEME_NAMES:
            actions.append(PaletteAction(
                f"Theme: {themeName}", "THEME",
                lambda name=themeName: cfg.set(cfg.totoneThemePreset, name),
                "totone color palette appearance",
            ))

        dlg = CommandPaletteDialog(actions, onUrlSubmitted=lambda u: self.addUrls([u]), parent=self)
        dlg.exec()
        dlg.deleteLater()

    def closeEvent(self, event) -> None:
        if event.spontaneous():
            event.ignore()
            self._onCloseClicked()
            return
        if not self.isMaximized():
            geo = self.geometry()
            cfg.set(cfg.geometry, (geo.x(), geo.y(), geo.width(), geo.height()))
        qrouter.unregister(self.stackedWidget)
        event.accept()

    def setVisible(self, visible: bool) -> None:
        # 主窗口隐藏时 setGeometry 不传给原生窗口，事件循环一跑就被改回，所以在首次显示前设置
        if visible and not self._isGeometryRestored:
            self._isGeometryRestored = True
            rect = QRect(*cfg.geometry.value)
            if rect.isValid() and QApplication.screenAt(rect.center()) is not None:
                self.setGeometry(rect)
            else:
                self.resize(960, 540)
                self.move(QApplication.primaryScreen().availableGeometry().center() - self.rect().center())
        if visible and not self.isVisible() and sys.platform == "win32":
            self._refreshBackgroundEffect()
        super().setVisible(visible)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.searchEdit.isVisible():
            self._refreshSearchEditGeometry()
        if sys.platform == "darwin":
            self._refreshBackgroundEffect()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if self._isBackgroundEffectDirty and event.type() == QEvent.Type.ThemeChange:
            self._isBackgroundEffectDirty = False
            self._refreshBackgroundEffect()

    def _setTheme(self, value, deferBackgroundRefresh: bool = False) -> None:
        prevTheme = qconfig.theme
        qconfig.theme = value
        if qconfig.theme != prevTheme:
            qconfig.themeChanged.emit(qconfig.theme)
        updateStyleSheet()
        qconfig.themeChangedFinished.emit()
        IconBodyLabel.clearCache()
        if (
            deferBackgroundRefresh
            and sys.platform == "win32"
            and cfg.backgroundEffect.value in {"Mica", "MicaBlur", "MicaAlt"}
        ):
            self._isBackgroundEffectDirty = True
            return
        self._isBackgroundEffectDirty = False
        self._refreshBackgroundEffect()

    def _onSystemColorSchemeChanged(self, colorScheme) -> None:
        if cfg.themeMode.value != Theme.AUTO:
            return
        if colorScheme == Qt.ColorScheme.Dark:
            self._setTheme(Theme.DARK, deferBackgroundRefresh=True)
        elif colorScheme == Qt.ColorScheme.Light:
            self._setTheme(Theme.LIGHT, deferBackgroundRefresh=True)
        else:
            self._setTheme(Theme.AUTO, deferBackgroundRefresh=True)

    def _refreshBackgroundEffect(self) -> None:
        if sys.platform == "win32":
            self._setBackgroundEffectWin(cfg.backgroundEffect.value)
        elif sys.platform == "darwin":
            self._setBackgroundEffectMac(cfg.backgroundEffect.value)

    def _setBackgroundEffectWin(self, value: str) -> None:
        isDark = isDarkTheme() if cfg.themeMode.value == Theme.AUTO else cfg.themeMode.value == Theme.DARK

        if value == "Acrylic":
            self.setStyleSheet(".MainWindow { background-color: transparent }")
            self.windowEffect.setAcrylicEffect(self.winId(), "00000030" if isDark else "FFFFFF30")
        elif value in {"Mica", "MicaBlur"}:
            self.setStyleSheet(".MainWindow { background-color: transparent }")
            self.windowEffect.setMicaEffect(self.winId(), isDark)
        elif value == "MicaAlt":
            self.setStyleSheet(".MainWindow { background-color: transparent }")
            self.windowEffect.setMicaEffect(self.winId(), isDark, isAlt=True)
        elif value == "Aero":
            self.setStyleSheet(".MainWindow { background-color: transparent }")
            self.windowEffect.setAeroEffect(self.winId())
            if isLessThanWin10():
                self.titleBar.closeBtn.hide()
                self.titleBar.minBtn.hide()
                self.titleBar.maxBtn.hide()
        elif value == "None":
            if isWin10():
                self.windowEffect.accentPolicy.AccentState = ACCENT_STATE.ACCENT_ENABLE_GRADIENT.value
                self.windowEffect.winCompAttrData.Attribute = WINDOWCOMPOSITIONATTRIB.WCA_ACCENT_POLICY.value
                self.windowEffect.SetWindowCompositionAttribute(int(self.winId()), pointer(self.windowEffect.winCompAttrData))
            else:
                self.windowEffect.winCompAttrData.Attribute = WINDOWCOMPOSITIONATTRIB.WCA_ACCENT_POLICY.value
                self.windowEffect.removeBackgroundEffect(self.winId())
            self.setStyleSheet("")
            if isLessThanWin10():
                self.titleBar.closeBtn.show()
                self.titleBar.minBtn.show()
                self.titleBar.maxBtn.show()

        self.backgroundColorAni.stop()
        self.setBackgroundColor(self._normalBackgroundColor())

    def paintEvent(self, e):
        if self._macVisualEffectView is not None:
            painter = QPainter(self)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(self.rect(), self.backgroundColor)
            self._updateSystemTitleBar()
            return
        super().paintEvent(e)

    def _setBackgroundEffectMac(self, value: str) -> None:
        if value == "None":
            self._removeMacAcrylicEffect()
            return

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if not self.isVisible():
            self.backgroundColorAni.stop()
            self.setBackgroundColor(self._normalBackgroundColor())
            return

        if self._macVisualEffectView is not None:
            self._setMacAcrylicAppearance()
            self.backgroundColorAni.stop()
            self.setBackgroundColor(self._normalBackgroundColor())
            return


        nsWindow = getNSWindow(self.winId())
        contentView = nsWindow.contentView()
        superview = contentView.superview() if contentView is not None else None
        if contentView is None or superview is None:
            return

        visualEffectView = Cocoa.NSVisualEffectView.new()
        visualEffectView.setAutoresizingMask_(Cocoa.NSViewWidthSizable | Cocoa.NSViewHeightSizable)
        visualEffectView.setFrame_(contentView.frame())
        visualEffectView.setState_(Cocoa.NSVisualEffectStateActive)
        visualEffectView.setMaterial_(Cocoa.NSVisualEffectMaterialUnderWindowBackground)
        visualEffectView.setBlendingMode_(Cocoa.NSVisualEffectBlendingModeBehindWindow)
        superview.addSubview_positioned_relativeTo_(
            visualEffectView, Cocoa.NSWindowBelow, contentView)

        nsWindow.setOpaque_(False)
        nsWindow.setBackgroundColor_(Cocoa.NSColor.clearColor())
        self._macVisualEffectView = visualEffectView
        self._setMacAcrylicAppearance()
        self.backgroundColorAni.stop()
        self.setBackgroundColor(self._normalBackgroundColor())
        self._updateSystemTitleBar()

    def _removeMacAcrylicEffect(self) -> None:
        if self._macVisualEffectView is not None:
            self._macVisualEffectView.removeFromSuperview()
            self._macVisualEffectView = None
            nsWindow = getNSWindow(self.winId())
            nsWindow.setOpaque_(True)
            nsWindow.setBackgroundColor_(Cocoa.NSColor.windowBackgroundColor())

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.backgroundColorAni.stop()
        self.setBackgroundColor(self._normalBackgroundColor())
        if self.isVisible():
            self._updateSystemTitleBar()

    def _setMacAcrylicAppearance(self) -> None:
        name = Cocoa.NSAppearanceNameDarkAqua if isDarkTheme() else Cocoa.NSAppearanceNameAqua
        self._macVisualEffectView.setAppearance_(Cocoa.NSAppearance.appearanceNamed_(name))

if sys.platform == "darwin":
    def _updateSystemTitleBar(self):
        self._extendTitleBarToClientArea()
        self.setSystemTitleBarButtonVisible(self.isSystemButtonVisible())
        nsWindow = self._MacFramelessWindowBase__nsWindow
        nsWindow.setMovableByWindowBackground_(False)
        nsWindow.setMovable_(False)
        nsWindow.setTitleVisibility_(Cocoa.NSWindowTitleHidden)

    MacFramelessWindowBase._updateSystemTitleBar = _updateSystemTitleBar


if sys.platform == "win32":
    from qframelesswindow.windows.c_structures import WINDOWCOMPOSITIONATTRIB
    from app.platform.windows import isLessThanWin10, isWin10

    if isWin10():
        from ctypes import pointer
        from ctypes.wintypes import MSG
        from qframelesswindow import AcrylicWindow, FramelessWindow, WindowEffect
        from qframelesswindow.windows.c_structures import ACCENT_STATE

        def _resetAcrylicEffect(self, hWnd):
            hWnd = int(hWnd)
            self.accentPolicy.AccentState = ACCENT_STATE.ACCENT_ENABLE_TRANSPARENTGRADIENT.value
            self.winCompAttrData.Attribute = WINDOWCOMPOSITIONATTRIB.WCA_ACCENT_POLICY.value
            self.SetWindowCompositionAttribute(hWnd, pointer(self.winCompAttrData))

        def _nativeEvent(self, eventType, message):
            if eventType == "windows_generic_MSG":
                msg = MSG.from_address(message.__int__())

                if cfg.backgroundEffect.value != "Acrylic":
                    return FramelessWindow.nativeEvent(self, eventType, message)

                WM_ENTERSIZEMOVE = 561
                WM_EXITSIZEMOVE = 562
                if msg.message == WM_ENTERSIZEMOVE:
                    self.windowEffect.resetAcrylicEffect(self.winId())
                elif msg.message == WM_EXITSIZEMOVE:
                    isDark = isDarkTheme() if cfg.themeMode.value == Theme.AUTO else cfg.themeMode.value == Theme.DARK
                    self.windowEffect.setAcrylicEffect(
                        self.winId(), "00000030" if isDark else "FFFFFF30",
                    )

            return FramelessWindow.nativeEvent(self, eventType, message)


        WindowEffect.resetAcrylicEffect = _resetAcrylicEffect
        MainWindow.updateFrameless = AcrylicWindow.updateFrameless
        MainWindow.nativeEvent = _nativeEvent
