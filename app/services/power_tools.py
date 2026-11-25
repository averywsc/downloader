from __future__ import annotations

import hashlib
import shutil
import subprocess
import tarfile
import threading
import zipfile
from datetime import datetime, time as dtime
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from loguru import logger
from PySide6.QtCore import QObject, QTimer, Signal

from app.config.cfg import cfg

if TYPE_CHECKING:
    from app.models.task import Task


ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")


def parseClockTime(text: str, fallback: dtime) -> dtime:
    try:
        parts = text.strip().split(":")
        return dtime(int(parts[0]) % 24, int(parts[1]) % 60)
    except Exception:
        return fallback


def isInQuietHours(now: datetime | None = None) -> bool:
    if not cfg.quietHoursEnabled.value:
        return False
    nowTime = (now or datetime.now()).time()
    start = parseClockTime(cfg.quietHoursStart.value, dtime(0, 0))
    end = parseClockTime(cfg.quietHoursEnd.value, dtime(7, 0))
    if start <= end:
        return start <= nowTime < end
    # Wraps across midnight (e.g. 23:00 -> 07:00)
    return nowTime >= start or nowTime < end


def matchSiteRule(url: str) -> dict | None:
    if not cfg.siteRulesEnabled.value or not url:
        return None
    host = (urlsplit(url).hostname or "").lower()
    if not host:
        return None
    for rule in cfg.siteRules.value or []:
        domain = str(rule.get("domain", "")).strip().lower().lstrip(".")
        if not domain:
            continue
        if host == domain or host.endswith("." + domain):
            return rule
    return None


def resolveSiteFolder(url: str) -> Path | None:
    rule = matchSiteRule(url)
    if not rule:
        return None
    folder = str(rule.get("folder", "")).strip()
    if not folder:
        return None
    p = Path(folder)
    if not p.is_absolute():
        p = Path(cfg.downloadFolder.value) / p
    return p


def detectHashAlgorithm(expected: str) -> str:
    clean = expected.strip().lower()
    if ":" in clean:
        prefix, _, digest = clean.partition(":")
        if prefix in ("md5", "sha1", "sha256", "sha512"):
            return prefix
        clean = digest
    lengthMap = {32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}
    return lengthMap.get(len(clean), "sha256")


def normalizeHash(expected: str) -> str:
    clean = expected.strip().lower()
    if ":" in clean:
        _, _, clean = clean.partition(":")
    return clean.strip()


def computeFileHash(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def virusTotalUrl(sha256: str) -> str:
    return f"https://www.virustotal.com/gui/file/{sha256.strip().lower()}"


def findFfmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    from app.config.paths import APP_DATA_DIR
    for candidate in (
        APP_DATA_DIR / "runtime" / "ffmpeg" / "ffmpeg.exe",
        APP_DATA_DIR / "runtime" / "ffmpeg" / "ffmpeg",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def safeExtractArchive(archivePath: Path) -> Path | None:
    nameLower = archivePath.name.lower()
    if not any(nameLower.endswith(ext) for ext in ARCHIVE_SUFFIXES):
        return None

    stem = archivePath.name
    for ext in (".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tar", ".zip"):
        if stem.lower().endswith(ext):
            stem = stem[:-len(ext)]
            break
    destDir = archivePath.parent / (stem or "extracted")
    destDir.mkdir(parents=True, exist_ok=True)
    destResolved = destDir.resolve()

    if nameLower.endswith(".zip"):
        with zipfile.ZipFile(archivePath, "r") as zf:
            for member in zf.infolist():
                target = (destDir / member.filename).resolve()
                if not str(target).startswith(str(destResolved)):
                    raise ValueError(f"Unsafe archive path: {member.filename}")
            zf.extractall(destDir)
    else:
        with tarfile.open(archivePath, "r:*") as tf:
            for member in tf.getmembers():
                target = (destDir / member.name).resolve()
                if not str(target).startswith(str(destResolved)):
                    raise ValueError(f"Unsafe archive path: {member.name}")
            tf.extractall(destDir)
    return destDir


def runAutoConvert(filePath: Path) -> Path | None:
    if not cfg.autoConvertEnabled.value:
        return None
    ext = filePath.suffix.lower()
    targetExt = None
    for rule in cfg.autoConvertRules.value or []:
        if not rule.get("enabled", True):
            continue
        if str(rule.get("fromExt", "")).strip().lower() == ext:
            targetExt = str(rule.get("toExt", "")).strip().lower()
            break
    if not targetExt or targetExt == ext:
        return None
    if not targetExt.startswith("."):
        targetExt = "." + targetExt

    ffmpeg = findFfmpeg()
    if not ffmpeg:
        logger.warning("Auto-convert skipped for {}: ffmpeg not found", filePath.name)
        return None

    outPath = filePath.with_suffix(targetExt)
    if outPath == filePath:
        outPath = filePath.with_name(f"{filePath.stem}_converted{targetExt}")

    cmd = [ffmpeg, "-y", "-i", str(filePath)]
    if ext == ".mkv" and targetExt == ".mp4":
        cmd += ["-c", "copy"]
    elif targetExt == ".mp3":
        cmd += ["-vn", "-q:a", "0"]
    elif targetExt == ".wav":
        cmd += ["-vn"]
    elif targetExt == ".flac":
        cmd += ["-vn", "-c:a", "flac"]
    cmd.append(str(outPath))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        logger.warning("Auto-convert failed for {}: {}", filePath.name, result.stderr[-300:])
        return None
    return outPath


class PowerToolsService(QObject):
    """Coordinates Dodown's post-download automation, quiet hours, and hash verification."""

    noticeRequested = Signal(str, str, str)  # level ("info"|"success"|"warning"|"error"), title, content
    quietHoursStateChanged = Signal(bool)

    def __init__(self, taskService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._taskService = taskService
        self._expectedHashes: dict[str, str] = {}
        self._wasInQuietHours = False
        self._preQuietSpeedLimit: bool | None = None

        self._quietTimer = QTimer(self)
        self._quietTimer.setInterval(30_000)
        self._quietTimer.timeout.connect(self._checkQuietHours)
        self._quietTimer.start()

        if hasattr(taskService, "taskCompleted"):
            taskService.taskCompleted.connect(self._onTaskCompleted)
        cfg.quietHoursEnabled.valueChanged.connect(lambda _: self._checkQuietHours())
        self._checkQuietHours()

    def registerExpectedHash(self, key: str, expectedHash: str) -> None:
        clean = normalizeHash(expectedHash)
        if key and clean:
            self._expectedHashes[key.strip()] = expectedHash.strip()

    def _checkQuietHours(self) -> None:
        active = isInQuietHours()
        if active == self._wasInQuietHours:
            return
        self._wasInQuietHours = active
        if active:
            self._preQuietSpeedLimit = bool(cfg.isSpeedLimitEnabled.value)
            if cfg.isSpeedLimitEnabled.value:
                cfg.set(cfg.isSpeedLimitEnabled, False)
                self.noticeRequested.emit(
                    "info", "Quiet Hours Active",
                    f"Speed limit uncapped ({cfg.quietHoursStart.value}–{cfg.quietHoursEnd.value}).",
                )
        else:
            if self._preQuietSpeedLimit is True and not cfg.isSpeedLimitEnabled.value:
                cfg.set(cfg.isSpeedLimitEnabled, True)
                self.noticeRequested.emit(
                    "info", "Quiet Hours Ended",
                    "Daytime speed limit restored.",
                )
            self._preQuietSpeedLimit = None
        self.quietHoursStateChanged.emit(active)

    def _onTaskCompleted(self, task: Task) -> None:
        outputPath = getattr(task, "outputPath", None)
        if not outputPath:
            return
        path = Path(outputPath)
        if not path.is_file():
            return
        url = str(getattr(task, "url", "") or "")
        expected = self._expectedHashes.pop(url, None) or self._expectedHashes.pop(path.name, None)

        threading.Thread(
            target=self._runPostProcessing,
            args=(path, expected),
            daemon=True,
        ).start()

    def _runPostProcessing(self, path: Path, expectedHash: str | None) -> None:
        # 1. Expected Hash Verification
        if expectedHash:
            try:
                algo = detectHashAlgorithm(expectedHash)
                actual = computeFileHash(path, algo)
                target = normalizeHash(expectedHash)
                if actual == target:
                    self.noticeRequested.emit(
                        "success", "Hash Verified",
                        f"{path.name} matched {algo.upper()} checksum.",
                    )
                else:
                    self.noticeRequested.emit(
                        "error", "Hash Mismatch",
                        f"{path.name} failed {algo.upper()} check!\nExpected: {target[:16]}…\nActual: {actual[:16]}…",
                    )
            except Exception as e:
                logger.warning("Hash check failed for {}: {}", path, e)

        # 2. Auto-Extract Archive
        if cfg.autoExtractArchives.value:
            try:
                dest = safeExtractArchive(path)
                if dest is not None:
                    if cfg.deleteArchiveAfterExtract.value:
                        path.unlink(missing_ok=True)
                    self.noticeRequested.emit(
                        "success", "Archive Extracted",
                        f"Extracted {path.name} → {dest.name}/",
                    )
            except Exception as e:
                logger.warning("Auto-extract failed for {}: {}", path, e)
                self.noticeRequested.emit("warning", "Auto-Extract Failed", f"{path.name}: {e}")

        # 3. Auto-Convert on Complete
        if cfg.autoConvertEnabled.value and path.is_file():
            try:
                out = runAutoConvert(path)
                if out is not None:
                    self.noticeRequested.emit(
                        "success", "Auto-Converted",
                        f"Converted {path.name} → {out.name}",
                    )
            except Exception as e:
                logger.warning("Auto-convert failed for {}: {}", path, e)
