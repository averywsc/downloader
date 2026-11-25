from __future__ import annotations

from typing import TYPE_CHECKING

from app.config.cfg import (
    BoolValidator,
    ConfigItem,
    OptionsConfigItem,
    OptionsValidator,
    RangeConfigItem,
    RangeValidator,
    StringListValidator,
)
from app.i18n import N
from app.models.pack import PackConfig

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from app.view.components.setting_card_group import CollapsibleSettingCardGroup

DEFAULT_TRACKER_LIST_SOURCES = [
    "https://trackerslist.com/best.txt",
    "https://cdn.jsdelivr.net/gh/XIU2/TrackersListCollection/best.txt",
    "https://ngosang.github.io/trackerslist/trackers_best.txt",
    "https://newtrackon.com/api/stable",
]


class BitTorrentConfig(PackConfig):
    enableDht = ConfigItem("BitTorrent", "EnableDHT", True, BoolValidator())
    enableLsd = ConfigItem("BitTorrent", "EnableLSD", True, BoolValidator())
    enableUtp = ConfigItem("BitTorrent", "EnableUTP", True, BoolValidator())
    encryptionMode = OptionsConfigItem(
        "BitTorrent", "EncryptionMode", "enabled", OptionsValidator(["enabled", "forced", "disabled"]),
    )
    enableWebTrackers = ConfigItem("BitTorrent", "EnableWebTrackers", True, BoolValidator())
    autoRefreshWebTrackers = ConfigItem("BitTorrent", "AutoRefreshWebTrackers", True, BoolValidator())
    saveMagnetFile = ConfigItem("BitTorrent", "SaveMagnetTorrentFile", False, BoolValidator())
    seedingRatioLimit = RangeConfigItem("BitTorrent", "SeedRatioLimitPercent", 0, RangeValidator(0, 10000))
    seedingTimeLimit = RangeConfigItem("BitTorrent", "SeedTimeLimitMinutes", 0, RangeValidator(0, 43200))
    maxConnections = RangeConfigItem("BitTorrent", "ConnectionsLimit", 500, RangeValidator(20, 2000))
    maxUploadSpeed = RangeConfigItem("BitTorrent", "UploadRateLimit", 0, RangeValidator(0, 1024 * 1024 * 100))
    listenPort = RangeConfigItem("BitTorrent", "ListenPort", 0, RangeValidator(0, 65535))
    metadataTimeout = RangeConfigItem("BitTorrent", "MetadataTimeout", 60, RangeValidator(5, 300))
    enableSequentialDownload = ConfigItem("BitTorrent", "SequentialDownload", False, BoolValidator())
    storageMode = OptionsConfigItem(
        "BitTorrent", "StorageMode", "sparse", OptionsValidator(["sparse", "allocate"]),
    )
    associateFileTypes = ConfigItem("BitTorrent", "AssociateFileTypes", False, BoolValidator())
    associateUriSchemes = ConfigItem("BitTorrent", "AssociateUriSchemes", False, BoolValidator())
    webTrackerSources = ConfigItem(
        "BitTorrent", "WebTrackerSources", DEFAULT_TRACKER_LIST_SOURCES, StringListValidator(),
    )
    webTrackerCustomList = ConfigItem("BitTorrent", "WebTrackerCustomList", "")

    def settingGroups(self, parent: QWidget) -> list[CollapsibleSettingCardGroup]:
        from qfluentwidgets import ComboBoxSettingCard, FluentIcon, PushSettingCard, RangeSettingCard, SwitchSettingCard
        from app.view.components.setting_card_group import CollapsibleSettingCardGroup
        from app.view.components.setting_cards import SpinBoxSettingCard
        from app.view.components.bootstrap_list import BootstrapListCard
        from .session import SessionState, btSession
        from .trackers import trackerList

        btGroup = CollapsibleSettingCardGroup(self.tr('BitTorrent'), "bittorrent", parent)

        stopCard = PushSettingCard(self.tr('Stop'), FluentIcon.CLOSE, self.tr('Stop BitTorrent Session'), self.tr('Not running'), btGroup)
        stopContent = {
            SessionState.STOPPED: self.tr('Not running'),
            SessionState.BUSY: self.tr('BitTorrent tasks are downloading or seeding; they must finish before stopping'),
            SessionState.IDLE: self.tr('Automatically stops after 5 minutes of inactivity; restarts automatically when a task starts'),
        }

        def refreshStopCard() -> None:
            stopCard.button.setEnabled(btSession.state == SessionState.IDLE)
            stopCard.setContent(stopContent[btSession.state])

        stopCard.clicked.connect(lambda: self.submit(btSession.stop()))
        btSession.stateChanged.connect(refreshStopCard, owner=stopCard)
        refreshStopCard()

        trackerListCard = BootstrapListCard(
            FluentIcon.GLOBE, self.tr('Tracker List'), trackerList,
            self.webTrackerSources, self.submit, btGroup,
            customItem=self.webTrackerCustomList, probeNetworkText=self._probeDhtText,
        )
        btSession.stateChanged.connect(trackerListCard.probeNetwork, owner=trackerListCard)

        cards = [
            stopCard,
            SpinBoxSettingCard(FluentIcon.GLOBE, self.tr('Port'),
                self.tr('0 for system assigned port'), "", self.listenPort, btGroup, 1),
            SpinBoxSettingCard(FluentIcon.HISTORY, self.tr('Metadata Download Timeout'),
                self.tr('Maximum loading time for metadata when parsing magnet links'), " s", self.metadataTimeout, btGroup, 5),
            RangeSettingCard(self.maxConnections, FluentIcon.PEOPLE, self.tr('Maximum Connections'),
                self.tr('Maximum connections per BT task session'), btGroup),
            SpinBoxSettingCard(FluentIcon.SHARE, self.tr('Seeding Upload Speed Limit'),
                self.tr('0 for unlimited, in KB/s per session'), " KB/s",
                self.maxUploadSpeed, btGroup, 64, 1 / 1024),
            SpinBoxSettingCard(FluentIcon.SHARE, self.tr('Auto Seeding Ratio Limit'),
                self.tr('0 means no seed ratio limit, 100% means a seed ratio of 1.0'), " %",
                self.seedingRatioLimit, btGroup, 50),
            SpinBoxSettingCard(FluentIcon.STOP_WATCH, self.tr('Auto Seeding Time Limit'),
                self.tr('0 means no seeding time limit'), " min",
                self.seedingTimeLimit, btGroup, 10),
            ComboBoxSettingCard(self.storageMode, FluentIcon.SAVE, self.tr('File Allocation Method'),
                self.tr('Sparse allocation minimizes disk writes; Pre-allocation allocates spaces in advance'),
                texts=[self.tr('Sparse allocation'), self.tr('Pre-allocation')], parent=btGroup),
            SwitchSettingCard(FluentIcon.SAVE, self.tr('Save Magnet Torrent File'),
                self.tr('Additionally save .torrent files when downloading magnet links or online torrents'), self.saveMagnetFile, btGroup),
            SwitchSettingCard(FluentIcon.LIBRARY, self.tr('Sequential Download'),
                self.tr('Download files sequentially, suitable for watching while downloading but may reduce overall efficiency'),
                self.enableSequentialDownload, btGroup),
            SwitchSettingCard(FluentIcon.GLOBE, self.tr('Enable DHT'),
                self.tr('Allow peer discovery via the Distributed Hash Table network'), self.enableDht, btGroup),
            SwitchSettingCard(FluentIcon.HOME, self.tr('Enable LSD'),
                self.tr('Broadcast and discover peers on local network for the same torrent'), self.enableLsd, btGroup),
            SwitchSettingCard(FluentIcon.SPEED_HIGH, self.tr('Enable uTP'),
                self.tr('Use uTP transport protocol for congestion control; only TCP is used when disabled'), self.enableUtp, btGroup),
            ComboBoxSettingCard(self.encryptionMode, FluentIcon.VPN, self.tr('Protocol Encryption'),
                self.tr('Obfuscate peer connection traffic to reduce ISP detection and throttling'),
                texts=[self.tr('Allow Encryption'), self.tr('Force Encryption'), self.tr('Disable Encryption')], parent=btGroup),
            SwitchSettingCard(FluentIcon.LINK, self.tr('Additional Tracker List'),
                self.tr('Merge tracker list into new BitTorrent tasks'),
                self.enableWebTrackers, btGroup),
            SwitchSettingCard(FluentIcon.SYNC, self.tr('Automatically Update Subscriptions'),
                self.tr('Update tracker list once daily in the background'),
                self.autoRefreshWebTrackers, btGroup),
            trackerListCard,
        ]
        btGroup.addSettingCards(cards)
        return [btGroup]

    async def _probeDhtText(self) -> tuple[str, dict]:
        from .session import btSession
        nodes = await btSession.probeDhtNodes()
        return ("", {}) if nodes is None else (N("BootstrapList", '{nodes} DHT node(s)'), {"nodes": nodes})


bittorrentConfig = BitTorrentConfig()
