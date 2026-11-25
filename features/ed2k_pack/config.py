from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from app.config.cfg import (
    BoolValidator, ConfigItem, RangeConfigItem, RangeValidator, StringListValidator, proxy,
)
from app.i18n import N

from app.config.serializers import PathSerializer
from app.config.paths import APP_DATA_DIR
from app.models.pack import BinaryRuntime, PackConfig
from app.platform.android import IS_ANDROID, nativeLibraryDir
from app.platform.arch import MACHINE_ARCH
from app.install import installFile
from app.platform.filesystem import findExecutable
from app.sources import Repo, fetchLatestRelease, fetchReleaseAsset

from .kelpie import PROXY_SCHEMES

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from app.view.components.setting_card_group import CollapsibleSettingCardGroup

KELPIE_REPO = Repo("XiaoYouChR/Kelpie", mirrors={"gitcode": "XiaoYouChR/Kelpie"})
DEFAULT_SERVER_LIST_SOURCES = [
    "https://upd.emule-security.org/server.met",
    "https://shortypower.org/server.met",
    "http://www.gruk.org/server.met",
]
DEFAULT_NODE_LIST_SOURCES = ["https://upd.emule-security.org/nodes.dat"]


class ED2kConfig(PackConfig):
    associateUriSchemes = ConfigItem("ED2k", "AssociateUriSchemes", False, BoolValidator())
    installFolder = ConfigItem("ED2k", "InstallFolder", f"{APP_DATA_DIR}/kelpie", serializer=PathSerializer(APP_DATA_DIR))
    enableKad = ConfigItem("ED2k", "EnableKad", True, BoolValidator())
    enableUpnp = ConfigItem("ED2k", "EnableUPnP", True, BoolValidator())
    listenPort = RangeConfigItem("ED2k", "ListenPort", 0, RangeValidator(0, 65535), restart=True)
    uploadRateLimit = RangeConfigItem("ED2k", "UploadRateLimit", 0, RangeValidator(0, 1024 * 1024 * 100))
    serverListSources = ConfigItem(
        "ED2k", "ServerListSources", DEFAULT_SERVER_LIST_SOURCES, StringListValidator(), restart=True,
    )
    nodeListSources = ConfigItem(
        "ED2k", "NodeListSources", DEFAULT_NODE_LIST_SOURCES, StringListValidator(), restart=True,
    )
    shouldRefreshLists = ConfigItem("ED2k", "ShouldRefreshLists", True, BoolValidator())
    seedingRatioLimit = RangeConfigItem("ED2k", "SeedRatioLimitPercent", 0, RangeValidator(0, 10000))
    seedingTimeLimit = RangeConfigItem("ED2k", "SharingTimeLimitMinutes", 0, RangeValidator(0, 43200))

    def settingGroups(self, parent: QWidget) -> list[CollapsibleSettingCardGroup]:
        from qfluentwidgets import FluentIcon, PushSettingCard, SwitchSettingCard
        from app.view.components.bootstrap_list import BootstrapListCard
        from app.view.components.setting_card_group import CollapsibleSettingCardGroup
        from app.view.components.setting_cards import SelectFolderSettingCard, SpinBoxSettingCard
        from .lists import nodeList, serverList
        from .session import ed2kSession

        group = CollapsibleSettingCardGroup(self.tr('eD2k'), "ed2k", parent)
        installFolderCard = SelectFolderSettingCard(
            self.installFolder, self.installFolder.defaultValue,
            self.tr('Kelpie Install Location'),
            group,
        )
        runtimeCard = self.createRuntimeCard(kelpieRuntime, group)

        installFolderCard.pathChanged.connect(runtimeCard._onInstallFolderChanged)

        def toStopCardContent() -> str:
            if ed2kSession.network is None:
                return self.tr('Not running')
            if not ed2kSession.isIdle:
                return self.tr('eD2k tasks are downloading or seeding; they must finish before termination')
            return self.tr('Automatically terminates after 5 minutes of inactivity; restarts automatically when an eD2k task starts')

        stopCard = PushSettingCard(
            self.tr('Terminate'), FluentIcon.CLOSE, self.tr('Terminate Kelpie Process'), toStopCardContent(), group,
        )

        def refreshStopCard():
            stopCard.button.setEnabled(ed2kSession.network is not None and ed2kSession.isIdle)
            stopCard.setContent(toStopCardContent())

        stopCard.clicked.connect(lambda: self.submit(ed2kSession.stop()))
        ed2kSession.networkChanged.connect(refreshStopCard, owner=stopCard)
        ed2kSession.runsChanged.connect(refreshStopCard, owner=stopCard)
        refreshStopCard()

        serverListCard = BootstrapListCard(
            FluentIcon.GLOBE, self.tr('Server List'), serverList,
            self.serverListSources, self.submit, group, probeNetworkText=self._probeServerText,
        )
        nodeListCard = BootstrapListCard(
            FluentIcon.GLOBE, self.tr('KAD Node List'), nodeList,
            self.nodeListSources, self.submit, group, probeNetworkText=self._probeKadText,
        )
        for card in (serverListCard, nodeListCard):
            ed2kSession.networkChanged.connect(card.probeNetwork, owner=card)

        group.addSettingCards([
            installFolderCard,
            runtimeCard,
            SwitchSettingCard(
                FluentIcon.SYNC, self.tr('Automatically Update Subscriptions'),
                self.tr('Update server list and KAD node list once daily in the background'),
                self.shouldRefreshLists, group,
            ),
            serverListCard,
            nodeListCard,
            stopCard,
            SwitchSettingCard(
                FluentIcon.WIFI, self.tr('Enable KAD'),
                self.tr('Discover sources via the KAD network; only eD2k servers are used if disabled'),
                self.enableKad, group,
            ),
            SwitchSettingCard(
                FluentIcon.GLOBE, self.tr('Enable UPnP'),
                self.tr('Automatically configure router port forwarding'),
                self.enableUpnp, group,
            ),
            SpinBoxSettingCard(
                FluentIcon.LINK, self.tr('Port'),
                self.tr('0 for system assigned port'), "",
                self.listenPort, group, 1,
            ),
            SpinBoxSettingCard(
                FluentIcon.SHARE, self.tr('Seeding Upload Speed Limit'),
                self.tr("0 for unlimited. The more you upload, the higher your score and the earlier you rank in others' queues, which also speeds up your own downloads"), " KB/s",
                self.uploadRateLimit, group, 64, 1 / 1024,
            ),
            SpinBoxSettingCard(
                FluentIcon.SHARE, self.tr('Auto Seeding Ratio Limit'),
                self.tr('0 means no seed ratio limit, 100% means a seed ratio of 1.0'), " %",
                self.seedingRatioLimit, group, 50,
            ),
            SpinBoxSettingCard(
                FluentIcon.STOP_WATCH, self.tr('Auto Seeding Time Limit'),
                self.tr('0 means no seeding time limit'), " min",
                self.seedingTimeLimit, group, 10,
            ),
        ])
        runtimeCard.refreshStatus()
        return [group]

    async def _probeServerText(self) -> tuple[str, dict]:
        from .session import ed2kSession
        network = ed2kSession.network
        if network is None:
            return N("BootstrapList", 'Not running'), {}
        if network.proxyIssue == "unreachable":
            return N("BootstrapList", 'Cannot Connect to Proxy'), {}
        if not network.isServerConnected:
            return N("BootstrapList", 'server disconnected'), {}
        if network.isHighId:
            return N("BootstrapList", 'connected to server (HighID)'), {}
        if proxy(PROXY_SCHEMES):
            return N("BootstrapList", 'connected to server (LowID; HighID unavailable when connected via proxy)'), {}
        if network.isBehindCarrierNat:
            return N("BootstrapList", 'connected to server (LowID; HighID unavailable due to carrier NAT)'), {}
        return N("BootstrapList", 'connected to server (LowID; enable UPnP or forward listening port on router to get HighID)'), {}

    async def _probeKadText(self) -> tuple[str, dict]:
        if not self.enableKad.value:
            return N("BootstrapList", 'KAD disabled'), {}
        from .session import ed2kSession
        network = ed2kSession.network
        if network is None:
            return N("BootstrapList", 'Not running'), {}
        if network.proxyIssue == "unreachable":
            return N("BootstrapList", 'Cannot Connect to Proxy'), {}
        if network.proxyIssue == "noUdp":
            return N("BootstrapList", 'Proxy does not forward UDP; KAD unavailable'), {}
        if network.isKadFirewalled:
            return N("BootstrapList", '{nodes} KAD node(s) (firewalled)'), {"nodes": network.kadNodes}
        return N("BootstrapList", '{nodes} KAD node(s)'), {"nodes": network.kadNodes}


ed2kConfig = ED2kConfig()


class KelpieRuntime(BinaryRuntime):
    name = "Kelpie"
    canInstall = not IS_ANDROID
    title = N("BinaryRuntime", 'eD2k/eMule')
    description = N("BinaryRuntime", 'Support for the eDonky network, enable downloading of archaic resources')
    icon = "BOOK_SHELF"

    def installFolder(self) -> Path:
        return Path(ed2kConfig.installFolder.value)

    def path(self) -> str:
        if IS_ANDROID:
            nativeDir = nativeLibraryDir()
            if not nativeDir:
                return ""
            binary = Path(nativeDir) / "libkelpie.so"
            return str(binary) if binary.exists() else ""
        return findExecutable(self.installFolder(), "kelpie")

    async def fetchLatestVersion(self) -> str:
        return (await fetchLatestRelease(KELPIE_REPO)).version

    def installedPaths(self) -> list[Path]:
        return [self.installFolder() / ("kelpie.exe" if sys.platform == "win32" else "kelpie")]

    async def install(self, version: str, onProgress: Callable[[float], None]) -> None:
        tag = version or await self.fetchLatestVersion()
        binary = self.installedPaths()[0]
        downloadPath = binary.with_name(f"{binary.name}.download")
        try:
            await fetchReleaseAsset(KELPIE_REPO, tag, buildAssetName(), downloadPath, onProgress)
            downloadPath.chmod(0o755)
            installFile(downloadPath, binary)
        finally:
            downloadPath.unlink(missing_ok=True)


def buildAssetName() -> str:
    arch = "arm64" if MACHINE_ARCH == "arm64" else "amd64"
    if sys.platform == "win32":
        return f"kelpie-windows-{arch}.exe"
    elif sys.platform == "darwin":
        return f"kelpie-darwin-{arch}"
    else:
        return f"kelpie-linux-{arch}"


kelpieRuntime = KelpieRuntime()
