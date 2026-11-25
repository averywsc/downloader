from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QDialog
from qfluentwidgets import CheckBox, Dialog, PushButton

from app.format import toReadableSize
from app.platform.desktop import raiseWindow
from app.services.name_conflict_queue import NameConflict, NameConflictQueue
from app.services.task_service import NameConflictChoice


def toContentText(conflict: NameConflict) -> str:
    modified = datetime.fromtimestamp(conflict.modifiedAt).strftime("%Y-%m-%d %H:%M")
    if conflict.isFolder:
        existing = QCoreApplication.translate("NameConflictDialog", 'Existing folder: {0} (modified)').format(modified)
    else:
        existing = QCoreApplication.translate("NameConflictDialog", 'Existing file: {0}, modified at {1}').format(toReadableSize(conflict.existingSize), modified)
    newSize = toReadableSize(conflict.task.fileSize) if conflict.task.fileSize > 0 else QCoreApplication.translate("NameConflictDialog", 'Unknown size')
    return "\n".join([existing, QCoreApplication.translate("NameConflictDialog", 'New file: {0}').format(newSize), QCoreApplication.translate("NameConflictDialog", 'When overwriting, the old file will be moved to the recycle bin.')])


class NameConflictDialog(Dialog):

    def __init__(self, conflict: NameConflict, queue: NameConflictQueue):
        super().__init__(QCoreApplication.translate("NameConflictDialog", '{0} already exists in the download directory').format(conflict.takenPath.name), toContentText(conflict))
        self._conflict = conflict
        self._queue = queue
        self._choice = NameConflictChoice.KEEP_BOTH

        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        self.setTitleBarVisible(False)
        self.yesButton.setText(QCoreApplication.translate("NameConflictDialog", 'Keep Both'))
        self.cancelButton.setText(QCoreApplication.translate("NameConflictDialog", 'Cancel'))
        self.overwriteButton = PushButton(QCoreApplication.translate("NameConflictDialog", 'Overwrite'), self.buttonGroup)
        self.restCheckBox = CheckBox(QCoreApplication.translate("NameConflictDialog", 'Apply the same action to the remaining {0} conflicts').format(self._conflict.restCount), self)
        self.restCheckBox.setVisible(self._conflict.restCount > 0)

    def _initLayout(self) -> None:
        self.textLayout.addWidget(self.restCheckBox)
        self.buttonLayout.insertWidget(1, self.overwriteButton, 1)
        self.adjustSize()
        self.setFixedSize(self.size())

    def _bind(self) -> None:
        self.overwriteButton.clicked.connect(self._onOverwriteClicked)
        self.finished.connect(self._onFinished)

    def _onOverwriteClicked(self) -> None:
        self._choice = NameConflictChoice.OVERWRITE
        self.accept()

    def _onFinished(self) -> None:
        taskId = self._conflict.task.taskId
        if self.result() == QDialog.DialogCode.Accepted:
            self._queue.setChoice(taskId, self._choice, self.restCheckBox.isChecked())
        else:
            self._queue.cancel(taskId)
        self.deleteLater()


class NameConflictPrompt:

    def __init__(self, queue: NameConflictQueue):
        self._queue = queue
        self._dialogs: set[NameConflictDialog] = set()
        queue.conflictChanged.connect(self._onConflictChanged)

    def _onConflictChanged(self, conflict: NameConflict | None) -> None:
        if conflict is None:
            return
        dialog = NameConflictDialog(conflict, self._queue)
        self._dialogs.add(dialog)
        dialog.destroyed.connect(lambda: self._dialogs.discard(dialog))
        dialog.show()
        raiseWindow(dialog)
