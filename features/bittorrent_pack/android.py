"""Android View adapter for BittorrentPack."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.i18n import N
from app.models.task import TaskStatus

if TYPE_CHECKING:
    from app.signal import Signal
    from .pack import BitTorrentPack
    from .task import BTTask

UI_CLASS = "com.xychr.ghostdownloader.features.bittorrent_pack.BitTorrentUi"


def init(pack: BitTorrentPack) -> dict[str, Signal]:
    from .session import btSession
    return {"sessionState": btSession.stateChanged}


def sessionState() -> str:
    from .session import btSession
    return btSession.state.value


async def stop() -> None:
    from .session import btSession
    await btSession.stop()

STATE_TEXT = {
    "checking_files": N("TaskState", 'Checking Existing Files'),
    "checking_resume_data": N("TaskState", 'Checking Resume Data'),
    "downloading_metadata": N("TaskState", 'Downloading Metadata'),
    "allocating": N("TaskState", 'Allocating Files'),
    "queued_for_checking": N("TaskState", 'Queued for Checks'),
}


def toStatusText(task: BTTask) -> str:
    if task.isSeeding:
        return N("TaskState", 'Seeding')
    if task.status == TaskStatus.COMPLETED:
        return ""
    return STATE_TEXT.get(task.stateText, "")


def taskFields(task: BTTask) -> dict:
    return {
        "progressMode": "hidden" if task.isSeeding else "determinate",
        "statusText": toStatusText(task),
        "secondarySpeed": task.uploadRate,
        "packFields": {
            "peers": {"active": task.peerCount, "total": task.totalPeerCount},
            "shareRatio": task.shareRatioPercent,
            "seedingSeconds": task.seedingTimeSeconds,
            "uploadSpeed": task.uploadRate,
        },
    }


async def trackerListState() -> dict:
    from dataclasses import asdict
    from .config import bittorrentConfig
    from .session import btSession
    from .trackers import trackerList

    return {
        "sources": list(bittorrentConfig.webTrackerSources.value),
        "defaults": list(bittorrentConfig.webTrackerSources.defaultValue),
        "custom": bittorrentConfig.webTrackerCustomList.value,
        "statuses": [asdict(status) for status in trackerList.statuses()],
        "entryCount": trackerList.entryCount(),
        "isRefreshing": trackerList.isRefreshing,
        "dhtNodes": await btSession.probeDhtNodes(),
    }


def setTrackerList(sources: str, custom: str) -> None:
    from app.config.cfg import cfg
    from .config import bittorrentConfig

    cfg.set(bittorrentConfig.webTrackerSources, list(dict.fromkeys(sources.split())))
    cfg.set(bittorrentConfig.webTrackerCustomList, custom)


async def refreshTrackerList() -> dict:
    from .trackers import trackerList

    await trackerList.refresh()
    return await trackerListState()
