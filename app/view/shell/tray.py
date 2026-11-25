from __future__ import annotations

import sys
from enum import Enum

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, QTimer, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMenu, QSystemTrayIcon
from qfluentwidgets import (
    Action, FluentIcon, FluentIconBase, FluentStyleSheet, RoundMenu, Theme,
    getIconColor, isDarkTheme,
)

from app.format import toReadableSize


class DodownIcon(FluentIconBase, Enum):
    DODOWN = "dodown"

    def path(self, theme=Theme.AUTO) -> str:
        from app.config.paths import EXECUTABLE_DIR
        local = EXECUTABLE_DIR / "app" / "assets" / "logo_menubar_template.png"
        if local.is_file():
            return str(local)
        return ":/image/logo_menubar_template.png"

    def _toTintedPixmap(self, theme: Theme) -> QPixmap:
        pixmap = QPixmap(self.path())
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(getIconColor(theme)))
        painter.end()
        return pixmap

    def icon(self, theme=Theme.AUTO, color=None) -> QIcon:
        return QIcon(self._toTintedPixmap(theme))

    def render(self, painter, rect, theme=Theme.AUTO, indexes=None, **attributes) -> None:
        painter.drawPixmap(QRectF(rect).toRect(), self._toTintedPixmap(theme))


def toAvailablePosition(position: QPoint, size: QSize, availableGeometry: QRect) -> QPoint:
    x = min(max(position.x(), availableGeometry.left()), availableGeometry.right() - size.width() + 1)
    y = min(max(position.y(), availableGeometry.top()), availableGeometry.bottom() - size.height() + 1)
    return QPoint(x, y)


if sys.platform == "win32":
    from typing import TYPE_CHECKING

    from PySide6.QtWidgets import QProxyStyle, QStyle, QStyleFactory
    from app.platform.windows import isGreaterEqualWin11
    from qfluentwidgets.common.screen import getCurrentScreenGeometry
    from qfluentwidgets.components.widgets.menu import MenuActionListWidget
    from qframelesswindow import WindowEffect

    if TYPE_CHECKING:
        from PySide6.QtGui import QAction

    class MenuStyle(QProxyStyle):

        def __init__(self, iconSize=14):
            super().__init__()
            self._iconSize = iconSize

        def pixelMetric(self, metric, option, widget):
            if metric == QStyle.PixelMetric.PM_SmallIconSize:
                return self._iconSize
            return super().pixelMetric(metric, option, widget)

        def polish(self, app, /):
            QStyleFactory.create("fusion").polish(app)

        def unpolish(self, app, /):
            QStyleFactory.create("fusion").polish(app)

    class AcrylicMenu(RoundMenu):

        def __init__(self, title="", parent=None):
            QMenu.__init__(self, parent)
            self.setTitle(title)
            self._icon = QIcon()
            self._actions: list[QAction] = []
            self._subMenus = []

            self.isSubMenu = False
            self.parentMenu = None
            self.menuItem = None
            self.lastHoverItem = None
            self.lastHoverSubMenuItem = None
            self.isHideBySystem = True
            self.itemHeight = 28

            self.hBoxLayout = QHBoxLayout(self)
            self.view = MenuActionListWidget(self)
            self.windowEffect = WindowEffect(self)

            self.aniManager = None
            self.timer = QTimer(self)

            self._initWidget()
            self._initLayout()
            self._bind()

        def _initWidget(self) -> None:
            self.setWindowFlags(
                Qt.WindowType.Popup
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.NoDropShadowWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setMouseTracking(True)
            self.setStyle(MenuStyle())
            self.timer.setSingleShot(True)
            self.timer.setInterval(400)

        def _initLayout(self) -> None:
            self.hBoxLayout.addWidget(self.view, 1, Qt.AlignmentFlag.AlignCenter)
            self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
            FluentStyleSheet.MENU.apply(self)
            self.view.setProperty("transparent", True)

        def _bind(self) -> None:
            self.timer.timeout.connect(self._onShowMenuTimeOut)
            self.view.itemClicked.connect(self._onItemClicked)
            self.view.itemEntered.connect(self._onItemEntered)

        def adjustPosition(self) -> None:
            self.move(toAvailablePosition(self.pos(), self.size(), getCurrentScreenGeometry()))

        def showEvent(self, event):
            self.windowEffect.addMenuShadowEffect(self.winId())
            self.windowEffect.addShadowEffect(self.winId())
            self.windowEffect.enableBlurBehindWindow(self.winId())
            from app.config.cfg import cfg
            dark = isDarkTheme() if cfg.themeMode.value == Theme.AUTO else cfg.themeMode.value == Theme.DARK
            self.windowEffect.setAcrylicEffect(
                self.winId(),
                "00000030" if dark else "FFFFFF30",
            )
            # 无 parent 时 fontMetrics 在首次显示前不准，基于正确屏幕重算
            for action in self._actions:
                item = action.property('item')
                if item:
                    self._adjustItemText(item, action)
            self.view.adjustSize()
            self.adjustSize()
            self.adjustPosition()
            self.raise_()
            self.activateWindow()
            self.setFocus()
            return super().showEvent(event)

        def paintEvent(self, e) -> None:
            painter = QPainter(self)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 1))
            painter.drawRect(self.rect())

    class TrayRoundMenu(RoundMenu):

        def adjustPosition(self) -> None:
            self.move(toAvailablePosition(self.pos(), self.size(), getCurrentScreenGeometry()))

        def showEvent(self, event):
            from app.view.totone_theme import currentPalette
            p = currentPalette()
            self.view.setStyleSheet(
                f"MenuActionListWidget {{ background-color: {p.panel}; border: 1px solid {p.edge}; "
                f"border-radius: 5px; padding: 4px; color: {p.ink}; }}"
                f"MenuActionListWidget::item {{ color: {p.ink}; border-radius: 3px; padding: 4px 8px; }}"
                f"MenuActionListWidget::item:hover, MenuActionListWidget::item:selected {{ "
                f"background-color: {p.line}; color: {p.ink}; }}"
            )
            self.adjustPosition()
            super().showEvent(event)

    TrayMenu = TrayRoundMenu
else:
    TrayMenu = RoundMenu


class SystemTrayIcon(QSystemTrayIcon):
    NAME = 'Dodown'

    def __init__(self, taskService, speedMeter, show, icon: QIcon, parent=None):
        super().__init__(icon, parent)
        self._taskService = taskService
        self._speedMeter = speedMeter
        self._show = show
        self.setToolTip(self.NAME)

        self._menu = TrayMenu()
        self._menu.addAction(Action(DodownIcon.DODOWN, self.tr('Dashboard'), self._menu,
                                    triggered=lambda: self._show().showTasks()))
        self._menu.addAction(Action(FluentIcon.ADD, self.tr('New Task'), self._menu,
                                    triggered=lambda: self._show().addUrls([])))
        self._menu.addAction(Action(FluentIcon.PLAY, self.tr('Start All'), self._menu,
                                    triggered=self._taskService.startAll))
        self._menu.addAction(Action(FluentIcon.PAUSE, self.tr('Pause All'), self._menu,
                                    triggered=self._taskService.pauseAll))
        self._menu.addAction(Action(FluentIcon.SETTING, self.tr('Settings'), self._menu,
                                    triggered=lambda: self._show().showSettings()))
        self._menu.addSeparator()
        self._menu.addAction(Action(FluentIcon.CLOSE, self.tr('Exit App'), self._menu,
                                    triggered=QApplication.instance().quit))
        self.setContextMenu(self._menu)
        self.destroyed.connect(self._menu.deleteLater)

        self.activated.connect(self._onActivated)
        self._speedMeter.speedChanged.connect(self._onSpeedChanged, owner=self)

    def _onActivated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show()

    def _onSpeedChanged(self, speed: int) -> None:
        if speed > 0:
            self.setToolTip(f"{self.NAME}\n↓ {toReadableSize(speed)}/s")
        else:
            self.setToolTip(self.NAME)
