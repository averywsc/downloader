from __future__ import annotations

import shutil
from collections import deque
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.config.cfg import cfg
from app.format import toReadableSize
from app.models.task import TaskStatus
from app.services.power_tools import isInQuietHours
from app.view.totone_theme import currentPalette


class SpeedSparkline(QWidget):
    """Rolling 60-second real-time download speed sparkline in the active Totone palette."""

    def __init__(self, maxSamples: int = 60, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._samples: deque[int] = deque([0] * maxSamples, maxlen=maxSamples)
        self.setFixedSize(112, 20)

    def push(self, speedBytesPerSec: int) -> None:
        self._samples.append(max(0, int(speedBytesPerSec)))
        self.update()

    def paintEvent(self, event) -> None:
        p = currentPalette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QColor(p.bg))
        painter.setPen(QPen(QColor(p.line), 1))
        painter.drawRoundedRect(rect, 3, 3)

        peak = max(self._samples) if self._samples else 0
        if peak <= 0:
            # Flat subtle baseline when idle
            y = rect.bottom() - 3
            painter.setPen(QPen(QColor(p.edge), 1))
            painter.drawLine(rect.left() + 3, y, rect.right() - 3, y)
            return

        n = len(self._samples)
        w = rect.width() - 4
        h = rect.height() - 4
        left = rect.left() + 2
        bottom = rect.bottom() - 2

        points = [
            QPointF(left + (w * i / max(1, n - 1)), bottom - (val / peak) * h)
            for i, val in enumerate(self._samples)
        ]

        linePath = QPainterPath(points[0])
        for pt in points[1:]:
            linePath.lineTo(pt)

        fillPath = QPainterPath(linePath)
        fillPath.lineTo(points[-1].x(), bottom)
        fillPath.lineTo(points[0].x(), bottom)
        fillPath.closeSubpath()

        acc = QColor(p.acc)
        grad = QLinearGradient(0, rect.top(), 0, bottom)
        topColor = QColor(acc)
        topColor.setAlpha(72)
        botColor = QColor(acc)
        botColor.setAlpha(6)
        grad.setColorAt(0.0, topColor)
        grad.setColorAt(1.0, botColor)
        painter.fillPath(fillPath, grad)

        painter.setPen(QPen(acc, 1.4))
        painter.drawPath(linePath)


class TotoneStatusBar(QWidget):
    """Totone-styled bottom status bar with live speed sparkline, counts, free space & quick toggles."""

    commandPaletteRequested = Signal()
    dropWidgetToggled = Signal(bool)

    def __init__(self, taskService, speedMeter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("totoneStatusBar")
        self.setFixedHeight(30)
        self._taskService = taskService
        self._speedMeter = speedMeter

        self.sparkline = SpeedSparkline(parent=self)
        self.speedLabel = QLabel("0.00 B/s", self)
        self.speedLabel.setObjectName("totoneStatusLabel")

        self.countsLabel = QLabel("0 active · 0 queued · 0 done", self)
        self.countsLabel.setObjectName("totoneStatusLabel")

        self.diskLabel = QLabel("Free: --", self)
        self.diskLabel.setObjectName("totoneStatusLabel")

        self.quietBadge = QLabel("Quiet Hours", self)
        self.quietBadge.setObjectName("totoneStatusLabel")
        self.quietBadge.hide()

        self.limitBtn = QPushButton("Limit: Off", self)
        self.limitBtn.setCheckable(True)
        self.limitBtn.setChecked(bool(cfg.isSpeedLimitEnabled.value))
        self.limitBtn.setFixedHeight(22)
        self.limitBtn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.dropBtn = QPushButton("Drop Pill", self)
        self.dropBtn.setCheckable(True)
        self.dropBtn.setChecked(bool(cfg.showFloatingDropZone.value))
        self.dropBtn.setFixedHeight(22)
        self.dropBtn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.cmdBtn = QPushButton("Ctrl+K", self)
        self.cmdBtn.setFixedHeight(22)
        self.cmdBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cmdBtn.setToolTip("Open Command Palette (Ctrl+K)")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)
        layout.addWidget(self.sparkline)
        layout.addWidget(self.speedLabel)
        layout.addWidget(self._sep())
        layout.addWidget(self.countsLabel)
        layout.addWidget(self._sep())
        layout.addWidget(self.diskLabel)
        layout.addWidget(self.quietBadge)
        layout.addStretch(1)
        layout.addWidget(self.limitBtn)
        layout.addWidget(self.dropBtn)
        layout.addWidget(self.cmdBtn)

        self._styleMiniButtons()

        self._diskTimer = QTimer(self)
        self._diskTimer.setInterval(10_000)
        self._diskTimer.timeout.connect(self.refreshDiskSpace)
        self._diskTimer.start()

        self._bind()
        self.refreshCounts()
        self.refreshDiskSpace()
        self.refreshLimitState()
        self.setQuietHoursActive(isInQuietHours())

    def _sep(self) -> QLabel:
        sep = QLabel("·", self)
        sep.setObjectName("totoneStatusLabel")
        return sep

    def _styleMiniButtons(self) -> None:
        p = currentPalette()
        qss = (
            f"QPushButton {{ font-size: 11px; padding: 1px 8px; border-radius: 3px; "
            f"background: {p.bg}; color: {p.mute}; border: 1px solid {p.line}; }}"
            f"QPushButton:hover {{ color: {p.ink}; border-color: {p.edge}; background: {p.line}; }}"
            f"QPushButton:checked {{ background: {p.acc}; color: {p.accink}; border-color: {p.acc}; font-weight: 700; }}"
        )
        for btn in (self.limitBtn, self.dropBtn, self.cmdBtn):
            btn.setStyleSheet(qss)
        self.quietBadge.setStyleSheet(
            f"color: {p.acc}; background: {p.line}; border: 1px solid {p.edge}; "
            f"border-radius: 3px; padding: 1px 6px; font-size: 10.5px; font-weight: 700;"
        )

    def refreshTheme(self) -> None:
        self._styleMiniButtons()
        self.sparkline.update()

    def _bind(self) -> None:
        self._speedMeter.speedChanged.connect(self._onSpeedChanged)
        for sigName in ("taskAdded", "taskRemoved", "taskStarted", "taskPaused", "taskCompleted", "taskFailed"):
            sig = getattr(self._taskService, sigName, None)
            if sig is not None:
                sig.connect(lambda *_: self.refreshCounts())
        self.limitBtn.clicked.connect(lambda checked: cfg.set(cfg.isSpeedLimitEnabled, checked))
        cfg.isSpeedLimitEnabled.valueChanged.connect(lambda _: self.refreshLimitState())
        self.dropBtn.clicked.connect(self._onDropBtnClicked)
        cfg.showFloatingDropZone.valueChanged.connect(lambda v: self.dropBtn.setChecked(bool(v)))
        self.cmdBtn.clicked.connect(self.commandPaletteRequested.emit)

    def _onDropBtnClicked(self, checked: bool) -> None:
        cfg.set(cfg.showFloatingDropZone, checked)
        self.dropWidgetToggled.emit(checked)

    def _onSpeedChanged(self, speed: int) -> None:
        self.sparkline.push(speed)
        self.speedLabel.setText(f"{toReadableSize(speed)}/s")

    def refreshCounts(self) -> None:
        try:
            tasks = list(self._taskService.tasks())
        except Exception:
            tasks = []
        active = sum(1 for t in tasks if t.status == TaskStatus.RUNNING)
        queued = sum(1 for t in tasks if t.status in (TaskStatus.WAITING, TaskStatus.PAUSED))
        done = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        self.countsLabel.setText(f"{active} active · {queued} queued · {done} done")

    def refreshDiskSpace(self) -> None:
        try:
            folder = Path(cfg.downloadFolder.value)
            target = folder if folder.exists() else folder.parent
            free = shutil.disk_usage(target).free
            self.diskLabel.setText(f"Free: {toReadableSize(free)}")
        except Exception:
            self.diskLabel.setText("Free: --")

    def refreshLimitState(self) -> None:
        enabled = bool(cfg.isSpeedLimitEnabled.value)
        self.limitBtn.setChecked(enabled)
        if enabled:
            cap = toReadableSize(int(cfg.speedLimitation.value))
            self.limitBtn.setText(f"Limit: {cap}/s")
        else:
            self.limitBtn.setText("Limit: Off")

    def setQuietHoursActive(self, active: bool) -> None:
        self.quietBadge.setVisible(bool(active))
