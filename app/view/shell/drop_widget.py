from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

from app.format import toReadableSize
from app.view.totone_theme import currentPalette


class FloatingDropWidget(QWidget):
    """Always-on-top Totone mini drop pill for quick drag-and-drop URLs & live speed."""

    urlsDropped = Signal(list)
    activateRequested = Signal()

    def __init__(self, speedMeter, taskService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._speedMeter = speedMeter
        self._taskService = taskService
        self._speedText = "0.00 B/s"
        self._activeCount = 0
        self._dragOver = False
        self._dragOffset: QPoint | None = None

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setFixedSize(172, 46)
        self.setToolTip("Drop URLs or .torrent files onto Dodown · Double-click to open")

        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() - 24, geo.bottom() - self.height() - 56)

        self._speedMeter.speedChanged.connect(self._onSpeedChanged)
        for sigName in ("taskAdded", "taskRemoved", "taskStarted", "taskPaused", "taskCompleted", "taskFailed"):
            sig = getattr(self._taskService, sigName, None)
            if sig is not None:
                sig.connect(lambda *_: self._refreshActive())
        self._refreshActive()

    def _onSpeedChanged(self, speed: int) -> None:
        self._speedText = f"{toReadableSize(speed)}/s"
        self.update()

    def _refreshActive(self) -> None:
        try:
            self._activeCount = int(self._taskService.runningCount())
        except Exception:
            self._activeCount = 0
        self.update()

    def paintEvent(self, event) -> None:
        p = currentPalette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setBrush(QColor(p.panel))
        borderColor = QColor(p.acc) if self._dragOver else QColor(p.edge)
        painter.setPen(QPen(borderColor, 2 if self._dragOver else 1))
        painter.drawRoundedRect(rect, 21, 21)

        # Left geometric "D" badge
        badge = rect.adjusted(7, 7, -(rect.width() - 35), -7)
        painter.setBrush(QColor(p.acc))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge, 14, 14)

        font = QFont("Archivo", 11, QFont.Weight.ExtraBold)
        painter.setFont(font)
        painter.setPen(QColor(p.accink))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "D")

        # Speed & status text
        textRect = rect.adjusted(44, 5, -12, -5)
        topRect = textRect.adjusted(0, 0, 0, -textRect.height() // 2)
        botRect = textRect.adjusted(0, textRect.height() // 2, 0, 0)

        painter.setFont(QFont("Archivo", 9, QFont.Weight.Bold))
        painter.setPen(QColor(p.ink))
        title = "Drop to queue" if self._dragOver else self._speedText
        painter.drawText(topRect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, title)

        painter.setFont(QFont("Archivo", 8))
        painter.setPen(QColor(p.mute))
        sub = f"Dodown · {self._activeCount} active"
        painter.drawText(botRect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, sub)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragOffset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._dragOffset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._dragOffset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._dragOffset = None

    def mouseDoubleClickEvent(self, event) -> None:
        self.activateRequested.emit()

    def dragEnterEvent(self, event) -> None:
        mime = event.mimeData()
        if mime.hasUrls() or (mime.hasText() and mime.text().strip()):
            self._dragOver = True
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._dragOver = False
        self.update()

    def dropEvent(self, event) -> None:
        self._dragOver = False
        self.update()
        mime = event.mimeData()
        if mime.hasUrls():
            urls = [u.toString() for u in mime.urls()]
        else:
            urls = [line.strip() for line in mime.text().splitlines() if line.strip()]
        if urls:
            self.urlsDropped.emit(urls)
            event.acceptProposedAction()
