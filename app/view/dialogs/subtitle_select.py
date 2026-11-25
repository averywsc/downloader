from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout
from qfluentwidgets import (
    BodyLabel, MessageBoxBase, PrimaryPushButton, PushButton, SubtitleLabel,
)

from app.view.components.tree_view import AutoSizingTreeView


class SubtitleSelectDialog(MessageBoxBase):

    def __init__(self, choices: list[tuple[str, str]], selected: list[str], parent=None):
        super().__init__(parent)
        self._choices = choices

        self.titleLabel = SubtitleLabel(self.tr('Select Subtitle Language'), self)
        self.summaryLabel = BodyLabel("", self)

        self.selectAllButton = PrimaryPushButton(self.tr('Select All'), self)
        self.clearButton = PushButton(self.tr('Select None'), self)

        self.treeView = AutoSizingTreeView(self, minimumVisibleRows=3)
        self.treeModel = QStandardItemModel(self.treeView)

        self._initWidget(set(selected))
        self._initLayout()
        self._bind()
        self._refreshSummary()

    def _initWidget(self, selected: set[str]) -> None:
        self.widget.setMinimumWidth(400)
        self.yesButton.setText(self.tr('Save'))
        self.cancelButton.setText(self.tr('Cancel'))

        self.treeView.setRootIsDecorated(False)
        self.treeView.setUniformRowHeights(True)
        self.treeView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.treeView.setHeaderHidden(True)
        self.treeView.setModel(self.treeModel)

        for langCode, label in self._choices:
            item = QStandardItem(label)
            item.setCheckable(True)
            item.setCheckState(Qt.CheckState.Checked if langCode in selected else Qt.CheckState.Unchecked)
            item.setData(langCode, Qt.ItemDataRole.UserRole)
            self.treeModel.appendRow(item)

    def _initLayout(self) -> None:
        actionsLayout = QHBoxLayout()
        actionsLayout.setContentsMargins(0, 0, 0, 0)
        actionsLayout.setSpacing(8)
        actionsLayout.addWidget(self.selectAllButton)
        actionsLayout.addWidget(self.clearButton)
        actionsLayout.addStretch(1)
        actionsLayout.addWidget(self.summaryLabel)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(8)
        self.viewLayout.addWidget(self.treeView)
        self.viewLayout.addSpacing(4)
        self.viewLayout.addLayout(actionsLayout)

    def _bind(self) -> None:
        self.selectAllButton.clicked.connect(lambda: self._setAll(True))
        self.clearButton.clicked.connect(lambda: self._setAll(False))
        self.treeModel.itemChanged.connect(lambda _: self._refreshSummary())

    def _setAll(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.treeModel.rowCount()):
            self.treeModel.item(row, 0).setCheckState(state)

    def _refreshSummary(self) -> None:
        count = sum(
            1 for row in range(self.treeModel.rowCount())
            if self.treeModel.item(row, 0).checkState() == Qt.CheckState.Checked
        )
        self.summaryLabel.setText(self.tr('{0}/{1} Languages').format(count, self.treeModel.rowCount()))

    def selectedLanguages(self) -> list[str]:
        return [
            self.treeModel.item(row, 0).data(Qt.ItemDataRole.UserRole)
            for row in range(self.treeModel.rowCount())
            if self.treeModel.item(row, 0).checkState() == Qt.CheckState.Checked
        ]
