from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from app.config.cfg import (
    BoolValidator,
    ConfigItem,
    OptionsConfigItem,
    OptionsValidator,
    RangeConfigItem,
    RangeValidator,
)
from app.i18n import N

from app.config.serializers import PathSerializer
from app.config.paths import APP_DATA_DIR
from app.install import installArchive
from app.models.pack import BinaryRuntime, PackConfig
from app.platform.android import IS_ANDROID, nativeLibraryDir
from app.platform.arch import MACHINE_ARCH
from app.platform.filesystem import findExecutable
from app.models.task import TaskError
from app.sources import Repo, fetchLatestRelease, fetchReleaseAsset

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from app.view.components.setting_card_group import CollapsibleSettingCardGroup

M3U8_REPO = Repo("nilaoda/N_m3u8DL-RE")


class M3U8Config(PackConfig):
    installFolder = ConfigItem("M3U8", "InstallFolder", f"{APP_DATA_DIR}/M3U8DL", serializer=PathSerializer(APP_DATA_DIR))
    associateFileTypes = ConfigItem("M3U8", "AssociateFileTypes", False, BoolValidator())
    outputFormat = OptionsConfigItem("M3U8", "OutputFormat", "mp4", OptionsValidator(["mp4", "mkv"]))
    threadCount = RangeConfigItem("M3U8", "ThreadCount", 8, RangeValidator(1, 64))
    retryCount = RangeConfigItem("M3U8", "RetryCount", 3, RangeValidator(0, 20))
    requestTimeout = RangeConfigItem("M3U8", "RequestTimeout", 100, RangeValidator(5, 600))
    shouldAutoSelect = ConfigItem("M3U8", "AutoSelect", True, BoolValidator())
    shouldConcurrentDownload = ConfigItem("M3U8", "ConcurrentDownload", True, BoolValidator())
    shouldAppendUrlParams = ConfigItem("M3U8", "AppendUrlParams", False, BoolValidator())
    shouldBinaryMerge = ConfigItem("M3U8", "BinaryMerge", False, BoolValidator())
    shouldCheckSegmentsCount = ConfigItem("M3U8", "CheckSegmentsCount", True, BoolValidator())
    shouldKeepLiveSegments = ConfigItem("M3U8", "LiveKeepSegments", False, BoolValidator())
    shouldFixLiveVtt = ConfigItem("M3U8", "LiveFixVtt", False, BoolValidator())
    liveWaitTime = RangeConfigItem("M3U8", "LiveWaitTime", 0, RangeValidator(0, 100000))
    liveTakeCount = RangeConfigItem("M3U8", "LiveTakeCount", 0, RangeValidator(0, 1000))
    decryptionEngine = OptionsConfigItem(
        "M3U8", "DecryptionEngine", "FFmpeg",
        OptionsValidator(["FFmpeg", "MP4Decrypt", "Shaka Packager"]),
    )
    decryptionBinaryPath = ConfigItem("M3U8", "DecryptionBinaryPath", "", serializer=PathSerializer(APP_DATA_DIR))
    shouldUseMp4RealTimeDecryption = ConfigItem("M3U8", "MP4RealTimeDecryption", True, BoolValidator())
    maxSpeed = RangeConfigItem("M3U8", "MaxSpeed", -1, RangeValidator(-1, 1000000))
    speedUnit = OptionsConfigItem("M3U8", "SpeedUnit", "Mbps", OptionsValidator(["Mbps", "Kbps"]))
    adKeyword = ConfigItem("M3U8", "AdKeyword", "")
    subtitleFormat = OptionsConfigItem("M3U8", "SubtitleFormat", "SRT", OptionsValidator(["SRT", "VTT"]))
    shouldOmitDateInfo = ConfigItem("M3U8", "NoDateInfo", False, BoolValidator())
    shouldKeepImageSegments = ConfigItem("M3U8", "KeepImageSegments", False, BoolValidator())
    shouldDeleteTemp = ConfigItem("M3U8", "DelAfterDone", True, BoolValidator())
    customMuxAfterDone = ConfigItem("M3U8", "CustomMuxAfterDone", "")
    shouldSelectAllAudioSubtitle = ConfigItem("M3U8", "SelectAllAudioSubtitle", True, BoolValidator())

    def settingGroups(self, parent: QWidget) -> list[CollapsibleSettingCardGroup]:
        import sys
        from qfluentwidgets import ComboBoxSettingCard, FluentIcon, RangeSettingCard, SwitchSettingCard
        from app.view.components.setting_card_group import CollapsibleSettingCardGroup
        from app.view.components.setting_cards import (
            SelectFolderSettingCard, LineEditSettingCard, SelectFileCard, SpinBoxSettingCard,
        )

        m3u8Group = CollapsibleSettingCardGroup(self.tr('M3U8 Playlist'), "m3u8", parent)
        installFolderCard = SelectFolderSettingCard(
            self.installFolder, f"{APP_DATA_DIR}/M3U8DL",
            self.tr('N_m3u8DL-RE Install Location'),
            m3u8Group,
        )
        runtimeCard = self.createRuntimeCard(m3u8Runtime, m3u8Group)

        cards = [installFolderCard, runtimeCard] + [
            ComboBoxSettingCard(self.outputFormat, FluentIcon.VIDEO, self.tr('Output Container'),
                self.tr('Prefered container format for ffmpeg to remux to after VOD download completion'), texts=["MP4", "MKV"], parent=m3u8Group),
            RangeSettingCard(self.threadCount, FluentIcon.CLOUD, self.tr('Chunk Threads'),
                self.tr('Download threads passed to N_m3u8DL-RE'), m3u8Group),
            RangeSettingCard(self.retryCount, FluentIcon.SYNC, self.tr('Chunk Retry Attempts'),
                self.tr('Maximum retries for failed chunks'), m3u8Group),
            SpinBoxSettingCard(FluentIcon.HISTORY, self.tr('Request Timeout'), self.tr('HTTP request timeout length'),
                " s", self.requestTimeout, m3u8Group, 5),
            SwitchSettingCard(FluentIcon.ACCEPT, self.tr('Auto Select Best Track'),
                self.tr('Default to best audio/video track'), self.shouldAutoSelect, m3u8Group),
            SwitchSettingCard(FluentIcon.PAUSE, self.tr('Simultaneous Audio/Video Download'),
                self.tr('Simultaneously download selected audio, video and subtitle tracks'), self.shouldConcurrentDownload, m3u8Group),
            SwitchSettingCard(FluentIcon.LINK, self.tr('Append URL Parameters'),
                self.tr('Append query parameters from input URL to chunk requests'), self.shouldAppendUrlParams, m3u8Group),
            SwitchSettingCard(FluentIcon.ALIGNMENT, self.tr('Binary Merge'),
                self.tr('Let N_m3u8DL-RE merge chunks in binary mode'), self.shouldBinaryMerge, m3u8Group),
            SwitchSettingCard(FluentIcon.SEARCH, self.tr('Verify Chunk Count'),
                self.tr('Verify chunk count is as expected after download completion'), self.shouldCheckSegmentsCount, m3u8Group),
            SwitchSettingCard(FluentIcon.SAVE, self.tr('Keep Original Live Stream Segments'),
                self.tr('Keep downloaded segments when merging live recordings in real time'), self.shouldKeepLiveSegments, m3u8Group),
            SwitchSettingCard(FluentIcon.FONT, self.tr('Correct VTT subtitles for live streams'),
                self.tr('Adjust VTT subtitle timeline based on audio start time'), self.shouldFixLiveVtt, m3u8Group),
            SpinBoxSettingCard(FluentIcon.STOP_WATCH, self.tr('Live Refresh Interval'),
                self.tr('Seconds between live playlist fetches, 0 for auto'), " s", self.liveWaitTime, m3u8Group, 1),
            SpinBoxSettingCard(FluentIcon.DOWNLOAD, self.tr('Live Segments Per Fetch'),
                self.tr('Max segments to fetch per refresh, 0 for auto'), "", self.liveTakeCount, m3u8Group, 1),
            ComboBoxSettingCard(self.decryptionEngine, FluentIcon.CERTIFICATE, self.tr('Decryption Engine'),
                self.tr('Third-party decryption program used'), texts=["FFmpeg", "MP4Decrypt", "Shaka Packager"], parent=m3u8Group),
            SelectFileCard(FluentIcon.COMMAND_PROMPT, self.tr('Decryption Engine Binary Location'),
                self.tr('Path to MP4Decrypt / Shaka Packager executable; leave empty to use FFmpeg'),
                configItem=self.decryptionBinaryPath, parent=m3u8Group),
            SwitchSettingCard(FluentIcon.FINGERPRINT, self.tr('MP4 Real-time Decryption'),
                self.tr('Decrypt MP4 segments in real time during download'), self.shouldUseMp4RealTimeDecryption, m3u8Group),
            SpinBoxSettingCard(FluentIcon.SPEED_HIGH, self.tr('Speed Limit'),
                self.tr('Maximum download speed, -1 for unlimited'), "", self.maxSpeed, m3u8Group, 1),
            ComboBoxSettingCard(self.speedUnit, FluentIcon.TAG, self.tr('Speed Limit Unit'),
                self.tr('Unit for speed limit value'), texts=["Mbps", "Kbps"], parent=m3u8Group),
            LineEditSettingCard(FluentIcon.REMOVE, self.tr('Ad Filter'),
                self.tr('Regex matching ad segment URLs'), self.adKeyword, m3u8Group, placeholder=self.tr('Regular Expression')),
            ComboBoxSettingCard(self.subtitleFormat, FluentIcon.DICTIONARY, self.tr('Subtitle Format'),
                self.tr('Subtitle output format'), texts=["SRT", "VTT"], parent=m3u8Group),
            SwitchSettingCard(FluentIcon.DATE_TIME, self.tr('Omit Date Info'),
                self.tr('Do not write date info during remux'), self.shouldOmitDateInfo, m3u8Group),
            SwitchSettingCard(FluentIcon.PHOTO, self.tr('Keep Graphical Segments'),
                self.tr('Keep original segments after converting graphical subtitles to images'), self.shouldKeepImageSegments, m3u8Group),
            SwitchSettingCard(FluentIcon.DELETE, self.tr('Delete Temp Files After Completion'),
                self.tr('Delete temporary segment storage directory after download'), self.shouldDeleteTemp, m3u8Group),
            SwitchSettingCard(FluentIcon.MUSIC, self.tr('Download All Audio Tracks'),
                self.tr('Fetch all audio tracks by default'), self.shouldSelectAllAudioSubtitle, m3u8Group),
            LineEditSettingCard(FluentIcon.VIDEO, self.tr('Custom Remux Arguments'),
                self.tr('Custom --mux-after-done; leave empty to auto-remux according to output container'),
                self.customMuxAfterDone, m3u8Group, placeholder="format=mp4"),
        ]
        m3u8Group.addSettingCards(cards)
        installFolderCard.pathChanged.connect(runtimeCard._onInstallFolderChanged)
        runtimeCard.refreshStatus()
        return [m3u8Group]


m3u8Config = M3U8Config()


class M3U8Runtime(BinaryRuntime):
    name = "N_m3u8DL-RE"
    binaryName = "N_m3u8DL-RE"
    canInstall = not IS_ANDROID
    title = N("BinaryRuntime", 'M3U8 & Live Stream Download')
    description = N("BinaryRuntime", 'Support for live streaming protocols including HLS and DASH, enable live stream recording')
    icon = "MEDIA"
    isRecommended = True

    def installFolder(self) -> Path:
        return Path(m3u8Config.installFolder.value)

    def path(self) -> str:
        if IS_ANDROID:
            nativeDir = nativeLibraryDir()
            if not nativeDir:
                return ""
            binary = Path(nativeDir) / "libnm3u8dlre.so"
            return str(binary) if binary.exists() else ""
        return findExecutable(self.installFolder(), "N_m3u8DL-RE")

    async def fetchLatestVersion(self) -> str:
        return (await fetchLatestRelease(M3U8_REPO)).version

    def installedPaths(self) -> list[Path]:
        suffix = ".exe" if sys.platform == "win32" else ""
        return [self.installFolder() / f"N_m3u8DL-RE{suffix}"]

    async def install(self, version: str, onProgress: Callable[[float], None]) -> None:
        if sys.platform == "win32":
            target = "win-arm64" if MACHINE_ARCH == "arm64" else "win-x64"
        elif sys.platform == "darwin":
            target = "osx-arm64" if MACHINE_ARCH == "arm64" else "osx-x64"
        elif sys.platform == "linux":
            target = "linux-arm64" if MACHINE_ARCH == "arm64" else "linux-x64"
        else:
            raise TaskError('N_m3u8DL-RE auto installation not supported on this platform: {platform}', platform=sys.platform)

        release = await fetchLatestRelease(M3U8_REPO)
        extension = ".zip" if sys.platform == "win32" else ".tar.gz"
        assetName = ""
        for asset in release.assets:
            if target in asset.name and asset.name.endswith(extension):
                assetName = asset.name
                break
        if not assetName:
            raise TaskError('No N_m3u8DL-RE installer package found for {target}', target=target)

        archive = self.installFolder() / assetName
        await fetchReleaseAsset(M3U8_REPO, release.version, assetName, archive, onProgress)
        await installArchive(archive, self.installFolder())


m3u8Runtime = M3U8Runtime()
