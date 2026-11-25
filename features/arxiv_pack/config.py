from __future__ import annotations

from typing import TYPE_CHECKING

from app.config.cfg import BoolValidator, ConfigItem
from app.models.pack import PackConfig

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from app.view.components.setting_card_group import CollapsibleSettingCardGroup


class ArxivConfig(PackConfig):
    isEnabled = ConfigItem("Arxiv", "Enabled", True, BoolValidator())
    shouldDownloadSource = ConfigItem("Arxiv", "DownloadSource", False, BoolValidator())
    shouldDownloadBibtex = ConfigItem("Arxiv", "DownloadBibtex", False, BoolValidator())

    def settingGroups(self, parent: QWidget) -> list[CollapsibleSettingCardGroup]:
        from qfluentwidgets import FluentIcon, SwitchSettingCard
        from app.view.components.setting_card_group import CollapsibleSettingCardGroup

        group = CollapsibleSettingCardGroup(self.tr('arXiv'), "arxiv", parent)
        group.addSettingCards([
            SwitchSettingCard(
                FluentIcon.LINK, self.tr('Parse arXiv Links'),
                self.tr('Download paper links, PDF links, and paper IDs as PDFs named by paper titles; parse as regular links if disabled'),
                self.isEnabled, group,
            ),
            SwitchSettingCard(
                FluentIcon.CODE, self.tr('Download TeX Source By Default'),
                self.tr('Download source archive by default for new tasks; can be modified per task in task draft'),
                self.shouldDownloadSource, group,
            ),
            SwitchSettingCard(
                FluentIcon.LIBRARY, self.tr('Download BibTeX By Default'),
                self.tr('Download .bib citation file by default for new tasks; can be modified per task in task draft'),
                self.shouldDownloadBibtex, group,
            ),
        ])
        return [group]


arxivConfig = ArxivConfig()
