from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from PySide6.QtCore import QCoreApplication, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QHBoxLayout

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FluentIcon,
    MessageBoxBase,
    PixmapLabel,
    PlainTextEdit,
    PrimaryPushButton,
    PushButton,
    SettingCard,
    SubtitleLabel,
)

if TYPE_CHECKING:
    from .account import BilibiliAccount
    from PySide6.QtWidgets import QWidget


def toQrPixmap(content: str, size: int = 240) -> QPixmap:
    import qrcode
    from qrcode.image.pure import PyPNGImage

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2, box_size=10)
    qr.add_data(content)
    qr.make(fit=True)
    buf = BytesIO()
    qr.make_image(image_factory=PyPNGImage).save(buf)
    pixmap = QPixmap()
    pixmap.loadFromData(buf.getvalue(), "PNG")
    return pixmap.scaled(size, size)


class ScanLoginDialog(MessageBoxBase):
    def __init__(self, account: BilibiliAccount, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._account = account
        self._loginUrl = ""

        self.widget.setFixedSize(430, 560)
        self.yesButton.hide()
        self.cancelButton.setText(self.tr('Close'))

        self.titleLabel = SubtitleLabel(self.tr('QR Code Login'), self.widget)
        self.descriptionLabel = CaptionLabel(
            self.tr('Use the Bilibili mobile app to scan the QR code below and confirm login on your phone.'),
            self.widget,
        )
        self.qrLabel = PixmapLabel(self.widget)
        self.qrLabel.setFixedSize(240, 240)
        self.qrLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qrLabel.setScaledContents(True)

        self.statusLabel = BodyLabel(self.tr('Fetching QR code...'), self.widget)
        self.tipLabel = CaptionLabel(
            self.tr('Code is valid for 180 seconds; select "Refresh QR Code" to generate a new code'),
            self.widget,
        )

        self.refreshButton = PrimaryPushButton(FluentIcon.SYNC, self.tr('Refresh QR Code'), self.widget)
        self.openBrowserButton = PushButton(FluentIcon.LINK, self.tr('Open Login Link'), self.widget)
        self.openBrowserButton.setEnabled(False)

        self._initWidget()
        self._initLayout()
        self._bind()
        self.reloadQrCode()

    def _initWidget(self):
        self.statusLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.statusLabel.setWordWrap(True)
        self.tipLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tipLabel.setWordWrap(True)

    def _initLayout(self):
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(12)
        buttonLayout.addWidget(self.refreshButton)
        buttonLayout.addWidget(self.openBrowserButton)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.descriptionLabel)
        self.viewLayout.addSpacing(12)
        self.viewLayout.addWidget(self.qrLabel, 0, Qt.AlignmentFlag.AlignCenter)
        self.viewLayout.addSpacing(8)
        self.viewLayout.addWidget(self.statusLabel)
        self.viewLayout.addWidget(self.tipLabel)
        self.viewLayout.addSpacing(6)
        self.viewLayout.addLayout(buttonLayout)

    def _bind(self):
        self.refreshButton.clicked.connect(self.reloadQrCode)
        self.openBrowserButton.clicked.connect(self._onOpenBrowser)
        self._account.qrStateChanged.connect(self._onQrState, owner=self)

    def reloadQrCode(self) -> None:
        self.qrLabel.setPixmap(QPixmap())
        self.qrLabel.setFixedSize(240, 240)
        self.statusLabel.setText(self.tr('Fetching QR code...'))
        self.openBrowserButton.setEnabled(False)
        self._loginUrl = ""
        self._account.startQrLogin()

    def _onQrState(self, statusCode: int, text: str):
        from .account import QR_EXPIRED, QR_LOGIN_SUCCESS, QR_UNSCANNED, QR_SCANNED
        if statusCode == QR_LOGIN_SUCCESS:
            self.statusLabel.setText(self.tr('Login succeeded. Importing Cookie...'))
            self.accept()
        elif statusCode == 0:
            self._loginUrl = text
            self.qrLabel.setPixmap(toQrPixmap(text))
            self.qrLabel.setFixedSize(240, 240)
            self.statusLabel.setText(self.tr('Please use the Bilibili app to scan QR code'))
            self.openBrowserButton.setEnabled(True)
        elif statusCode == QR_UNSCANNED:
            self.statusLabel.setText(self.tr('Waiting for scan'))
        elif statusCode == QR_SCANNED:
            self.statusLabel.setText(self.tr('QR code scanned. Please confirm login on your phone.'))
        elif statusCode == QR_EXPIRED:
            self.statusLabel.setText(self.tr('Code expired, select "Refresh QR Code" to generate a new code'))
        else:
            self.statusLabel.setText(
                QCoreApplication.translate("TaskErrors", text) if text else str(statusCode)
            )

    def _onOpenBrowser(self):
        if self._loginUrl:
            QDesktopServices.openUrl(QUrl(self._loginUrl))

    def done(self, code: int) -> None:
        self._account.cancelQrLogin()
        super().done(code)


class EditCookieDialog(MessageBoxBase):
    def __init__(self, parent: QWidget | None = None, initialCookie: str = "") -> None:
        super().__init__(parent)

        self.widget.setFixedSize(420, 500)
        self.yesButton.setText(self.tr('Save'))
        self.cancelButton.setText(self.tr('Cancel'))

        self.titleLabel = SubtitleLabel(self.tr('Import Cookie Manually'), self.widget)
        self.descriptionLabel = CaptionLabel(
            self.tr('Paste the full Cookie exported from the browser. Save with it empty to clear the current Cookie.'), self.widget,
        )
        self.cookieTextEdit = PlainTextEdit(self.widget)
        self.cookieTextEdit.setPlaceholderText(self.tr('Enter user Cookie here'))
        self.cookieTextEdit.setPlainText(initialCookie or "")

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.descriptionLabel)
        self.viewLayout.addWidget(self.cookieTextEdit)


class BilibiliLoginSettingCard(SettingCard):
    def __init__(self, account: BilibiliAccount, parent: QWidget | None = None) -> None:
        self._account = account
        super().__init__(
            FluentIcon.VIEW, self.tr('Account Login'),
            self.tr('Status: Not logged in'), parent,
        )
        self.scanButton = PrimaryPushButton(self.tr('QR Code Login'), self)
        self.editButton = PushButton(self.tr('Import Cookie'), self)
        self.logoutButton = PushButton(self.tr('Logout'), self)

        self._initLayout()
        self._bind()
        self.refreshLoginInfo()

    def _initLayout(self):
        self.hBoxLayout.addWidget(self.scanButton, 0)
        self.hBoxLayout.addSpacing(8)
        self.hBoxLayout.addWidget(self.editButton, 0)
        self.hBoxLayout.addSpacing(8)
        self.hBoxLayout.addWidget(self.logoutButton, 0)
        self.hBoxLayout.addSpacing(16)

    def _bind(self):
        self.scanButton.clicked.connect(self._onScanLogin)
        self.editButton.clicked.connect(self._onEditCookie)
        self.logoutButton.clicked.connect(self._onLogout)
        self._account.accountChanged.connect(self.refreshLoginInfo, owner=self)

    def refreshLoginInfo(self) -> None:
        if self._account.isLoggedIn:
            uname = self._account.username or "-"
            mid = self._account.mid or "-"
            vip = self._account.vip or "未开通"
            self.setContent(
                self.tr('Status: Logged in, User: {0}, UID: {1}, Membership: {2}').format(uname, mid, vip)
            )
        else:
            self.setContent(self.tr('Status: Not logged in'))
        self.scanButton.setEnabled(True)
        self.editButton.setEnabled(True)
        self.logoutButton.setEnabled(self._account.isLoggedIn)

    def _onScanLogin(self):
        dialog = ScanLoginDialog(self._account, self.window())
        dialog.exec()
        dialog.deleteLater()

    def _onEditCookie(self):
        from .account import toCookie
        dialog = EditCookieDialog(self.window(), self._account.cookie)
        if not dialog.exec():
            dialog.deleteLater()
            return

        newCookie = toCookie(dialog.cookieTextEdit.toPlainText())
        dialog.deleteLater()
        if not newCookie:
            self._account.setCookie("")
            return

        self._account.setCookie(newCookie)

    def _onLogout(self):
        self.scanButton.setEnabled(False)
        self.editButton.setEnabled(False)
        self.logoutButton.setEnabled(False)
        self.setContent(self.tr('Logging out...'))
        self._account.logout()
