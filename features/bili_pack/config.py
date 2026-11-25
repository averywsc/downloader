from __future__ import annotations

from typing import TYPE_CHECKING

from app.config.cfg import ConfigItem, OptionsConfigItem, OptionsValidator
from app.i18n import N
from app.models.pack import PackConfig

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from app.view.components.setting_card_group import CollapsibleSettingCardGroup
    from .account import BilibiliAccount

QUALITY_VALUES = [16, 32, 64, 74, 80, 112, 116, 120, 125, 126, 127]
QUALITY_LABELS = [
    "360P", "480P", "720P", "720P60", "1080P", "1080P+",
    "1080P60", "4K", "HDR", N("BilibiliConfig", 'Dolby Vision'), "8K",
]
AUDIO_QUALITY_VALUES = [30216, 30232, 30280, 30250, 30251]
AUDIO_QUALITY_LABELS = ["64K", "132K", "192K", N("BilibiliConfig", 'Dolby Atmos'), "Hi-Res"]


class BilibiliConfig(PackConfig):
    _account: BilibiliAccount
    userCookie = ConfigItem("Bilibili", "UserCookie", "")
    defaultQuality = OptionsConfigItem(
        "Bilibili", "DefaultQuality", 80, OptionsValidator(QUALITY_VALUES),
    )
    defaultAudioQuality = OptionsConfigItem(
        "Bilibili", "DefaultAudioQuality", 30280, OptionsValidator(AUDIO_QUALITY_VALUES),
    )
    defaultDanmaku = OptionsConfigItem(
        "Bilibili", "DefaultDanmaku", "none", OptionsValidator(["none", "ass", "xml"]),
    )
    alternativeQuality = OptionsConfigItem(
        "Bilibili", "AlternativeQuality", "max", OptionsValidator(["max", "min"]),
    )

    def settingGroups(self, parent: QWidget) -> list[CollapsibleSettingCardGroup]:
        from qfluentwidgets import ComboBoxSettingCard, FluentIcon
        from app.view.components.setting_card_group import CollapsibleSettingCardGroup
        from .setting_cards import BilibiliLoginSettingCard

        group = CollapsibleSettingCardGroup(self.tr('Bilibili'), "bilibili", parent)
        group.addSettingCards([
            BilibiliLoginSettingCard(self._account, group),
            ComboBoxSettingCard(self.defaultQuality, FluentIcon.VIDEO, self.tr('Default Quality'),
                                self.tr('Select preferred default video quality'),
                                texts=[self.tr(x) for x in QUALITY_LABELS], parent=group),
            ComboBoxSettingCard(self.defaultAudioQuality, FluentIcon.MUSIC, self.tr('Default Audio Quality'),
                                self.tr('Select preferred default audio quality'),
                                texts=[self.tr(x) for x in AUDIO_QUALITY_LABELS], parent=group),
            ComboBoxSettingCard(self.defaultDanmaku, FluentIcon.CHAT, self.tr('Default Danmaku'),
                                self.tr('Select the default danmaku format for downloads'),
                                texts=[self.tr('Skip'), "ASS", "XML"], parent=group),
            ComboBoxSettingCard(self.alternativeQuality, FluentIcon.SPEED_HIGH, self.tr('When Quality Unavailable'),
                                self.tr('Fallback logic when selected video or audio quality is unavailable'),
                                texts=[self.tr('Choose Highest'), self.tr('Choose Lowest')],
                                parent=group),
        ])
        return [group]


bilibiliConfig = BilibiliConfig()
