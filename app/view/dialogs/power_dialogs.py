from __future__ import annotations

import json
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    BodyLabel, CaptionLabel, CheckBox, LineEdit, MessageBoxBase, PrimaryPushButton,
    PushButton, SubtitleLabel,
)

from app.config.cfg import cfg
from app.services.power_tools import (
    computeFileHash, detectHashAlgorithm, findFfmpeg, normalizeHash, virusTotalUrl,
)


def _findYtDlp() -> str | None:
    found = shutil.which("yt-dlp")
    if found:
        return found
    from app.config.paths import APP_DATA_DIR
    for candidate in (
        APP_DATA_DIR / "runtime" / "yt-dlp" / "yt-dlp.exe",
        APP_DATA_DIR / "runtime" / "yt-dlp" / "yt-dlp",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


MEDIA_PRESETS: dict[str, tuple[str, list[str]]] = {
    "Best MP4": (
        "Best video + audio muxed into MP4",
        ["-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b", "--merge-output-format", "mp4"],
    ),
    "Audio MP3": (
        "Extract high-quality MP3 audio",
        ["-x", "--audio-format", "mp3", "--audio-quality", "0"],
    ),
    "Lossless FLAC": (
        "Extract lossless FLAC audio",
        ["-x", "--audio-format", "flac"],
    ),
    "Studio WAV": (
        "Extract uncompressed WAV (ready for Bebeat / DAW)",
        ["-x", "--audio-format", "wav"],
    ),
}


class MediaStudioDialog(MessageBoxBase):
    """One-Click Media Presets (yt-dlp + FFmpeg), Timestamp Clipping & Playlist Batch Picker."""

    _playlistLoaded = Signal(list, str)
    _logLine = Signal(str)
    _downloadDone = Signal(bool, str)

    def __init__(self, onQueueUrls: Callable[[list[str]], None] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._onQueueUrls = onQueueUrls
        self._selectedPreset = "Best MP4"
        self._playlistEntries: list[dict] = []

        self.widget.setFixedWidth(640)
        self.titleLabel = SubtitleLabel("Media & Playlist Studio", self)
        self.subtitleLabel = CaptionLabel(
            "One-click MP4 / MP3 / FLAC / WAV presets, timestamp clipping, and playlist batch picker.", self
        )

        self.urlEdit = LineEdit(self)
        self.urlEdit.setPlaceholderText("Paste a YouTube, SoundCloud, Bandcamp, or playlist URL...")
        self.loadPlaylistBtn = PushButton("Load Playlist", self)

        urlRow = QHBoxLayout()
        urlRow.setSpacing(8)
        urlRow.addWidget(self.urlEdit, 1)
        urlRow.addWidget(self.loadPlaylistBtn)

        # One-click preset buttons
        presetRow = QHBoxLayout()
        presetRow.setSpacing(6)
        self._presetButtons: dict[str, PushButton] = {}
        for name, (tip, _) in MEDIA_PRESETS.items():
            btn = PushButton(name, self)
            btn.setCheckable(True)
            btn.setChecked(name == self._selectedPreset)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda checked=False, n=name: self._selectPreset(n))
            self._presetButtons[name] = btn
            presetRow.addWidget(btn)

        # Timestamp clipping row
        clipRow = QHBoxLayout()
        clipRow.setSpacing(8)
        self.clipStartEdit = LineEdit(self)
        self.clipStartEdit.setPlaceholderText("Start (e.g. 00:45)")
        self.clipEndEdit = LineEdit(self)
        self.clipEndEdit.setPlaceholderText("End (e.g. 01:12)")
        clipRow.addWidget(BodyLabel("Clip range (optional):", self))
        clipRow.addWidget(self.clipStartEdit)
        clipRow.addWidget(BodyLabel("to", self))
        clipRow.addWidget(self.clipEndEdit)

        # Options row
        optRow = QHBoxLayout()
        optRow.setSpacing(14)
        self.embedMetaCheck = CheckBox("Embed Thumbnail & Metadata", self)
        self.embedMetaCheck.setChecked(True)
        self.numberItemsCheck = CheckBox("Number Playlist Items", self)
        self.numberItemsCheck.setChecked(True)
        optRow.addWidget(self.embedMetaCheck)
        optRow.addWidget(self.numberItemsCheck)
        optRow.addStretch(1)

        # Playlist item picker
        self.playlistWidget = QListWidget(self)
        self.playlistWidget.setMaximumHeight(165)
        self.playlistWidget.hide()

        self.playlistActions = QWidget(self)
        paLayout = QHBoxLayout(self.playlistActions)
        paLayout.setContentsMargins(0, 0, 0, 0)
        self.selectAllBtn = PushButton("Select All", self.playlistActions)
        self.selectNoneBtn = PushButton("Select None", self.playlistActions)
        self.playlistCountLabel = CaptionLabel("", self.playlistActions)
        paLayout.addWidget(self.selectAllBtn)
        paLayout.addWidget(self.selectNoneBtn)
        paLayout.addStretch(1)
        paLayout.addWidget(self.playlistCountLabel)
        self.playlistActions.hide()

        self.logOutput = QPlainTextEdit(self)
        self.logOutput.setReadOnly(True)
        self.logOutput.setMaximumHeight(110)
        self.logOutput.setPlaceholderText("Status output will appear here...")

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.subtitleLabel)
        self.viewLayout.addLayout(urlRow)
        self.viewLayout.addLayout(presetRow)
        self.viewLayout.addLayout(clipRow)
        self.viewLayout.addLayout(optRow)
        self.viewLayout.addWidget(self.playlistActions)
        self.viewLayout.addWidget(self.playlistWidget)
        self.viewLayout.addWidget(self.logOutput)

        self.yesButton.setText("Start Download")
        self.cancelButton.setText("Close")

        self.loadPlaylistBtn.clicked.connect(self._loadPlaylist)
        self.selectAllBtn.clicked.connect(lambda: self._setAllChecked(True))
        self.selectNoneBtn.clicked.connect(lambda: self._setAllChecked(False))
        self._playlistLoaded.connect(self._onPlaylistLoaded)
        self._logLine.connect(self.logOutput.appendPlainText)
        self._downloadDone.connect(self._onDownloadDone)

        # Override accept so dialog stays open while yt-dlp runs
        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self._startDownload)

    def _selectPreset(self, name: str) -> None:
        self._selectedPreset = name
        for k, btn in self._presetButtons.items():
            btn.setChecked(k == name)

    def _setAllChecked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.playlistWidget.count()):
            self.playlistWidget.item(i).setCheckState(state)

    def _loadPlaylist(self) -> None:
        url = self.urlEdit.text().strip()
        if not url:
            self.logOutput.appendPlainText("Enter a playlist or channel URL first.")
            return
        ytdlp = _findYtDlp()
        if not ytdlp:
            self.logOutput.appendPlainText("yt-dlp executable not found on PATH or in Dodown runtime.")
            return
        self.loadPlaylistBtn.setEnabled(False)
        self.logOutput.appendPlainText(f"Inspecting playlist: {url}")

        def worker():
            try:
                res = subprocess.run(
                    [ytdlp, "--flat-playlist", "-J", url],
                    capture_output=True, text=True, timeout=60,
                )
                if res.returncode != 0:
                    self._playlistLoaded.emit([], res.stderr.strip()[:240] or "Failed to load playlist.")
                    return
                data = json.loads(res.stdout)
                entries = data.get("entries") or []
                items = []
                for idx, entry in enumerate(entries, 1):
                    if not isinstance(entry, dict):
                        continue
                    title = entry.get("title") or entry.get("id") or f"Item {idx}"
                    eurl = entry.get("url") or entry.get("webpage_url") or ""
                    if eurl and not eurl.startswith("http"):
                        eurl = f"https://www.youtube.com/watch?v={eurl}"
                    items.append({"index": idx, "title": title, "url": eurl})
                self._playlistLoaded.emit(items, "")
            except Exception as e:
                self._playlistLoaded.emit([], str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _onPlaylistLoaded(self, items: list[dict], error: str) -> None:
        self.loadPlaylistBtn.setEnabled(True)
        if error:
            self.logOutput.appendPlainText(f"Error: {error}")
            return
        self._playlistEntries = items
        self.playlistWidget.clear()
        for item in items:
            li = QListWidgetItem(f"{item['index']:02d}. {item['title']}")
            li.setFlags(li.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            li.setCheckState(Qt.CheckState.Checked)
            li.setData(Qt.ItemDataRole.UserRole, item["url"])
            self.playlistWidget.addItem(li)
        self.playlistCountLabel.setText(f"{len(items)} items loaded")
        self.playlistActions.setVisible(bool(items))
        self.playlistWidget.setVisible(bool(items))
        self.logOutput.appendPlainText(f"Loaded {len(items)} playlist items.")

    def _startDownload(self) -> None:
        urls: list[str] = []
        if self.playlistWidget.isVisible() and self.playlistWidget.count() > 0:
            for i in range(self.playlistWidget.count()):
                it = self.playlistWidget.item(i)
                if it.checkState() == Qt.CheckState.Checked:
                    u = it.data(Qt.ItemDataRole.UserRole)
                    if u:
                        urls.append(str(u))
        else:
            raw = self.urlEdit.text().strip()
            if raw:
                urls = [raw]

        if not urls:
            self.logOutput.appendPlainText("Please enter a URL or select at least one playlist item.")
            return

        ytdlp = _findYtDlp()
        if not ytdlp:
            if self._onQueueUrls is not None:
                self._onQueueUrls(urls)
                self.accept()
                return
            self.logOutput.appendPlainText("yt-dlp not found. Install yt-dlp in Settings or add it to PATH.")
            return

        _, presetArgs = MEDIA_PRESETS[self._selectedPreset]
        outDir = Path(cfg.downloadFolder.value)
        outDir.mkdir(parents=True, exist_ok=True)
        template = (
            str(outDir / "%(autonumber)02d - %(title)s.%(ext)s")
            if (self.numberItemsCheck.isChecked() and len(urls) > 1)
            else str(outDir / "%(title)s.%(ext)s")
        )

        cmd = [ytdlp, *presetArgs, "-o", template]
        ffmpeg = findFfmpeg()
        if ffmpeg:
            cmd += ["--ffmpeg-location", str(Path(ffmpeg).parent)]
        if self.embedMetaCheck.isChecked():
            cmd += ["--embed-thumbnail", "--add-metadata"]
        start = self.clipStartEdit.text().strip()
        end = self.clipEndEdit.text().strip()
        if start or end:
            cmd += ["--download-sections", f"*{start or '00:00'}-{end or 'inf'}"]
        cmd += urls

        self.yesButton.setEnabled(False)
        self.logOutput.appendPlainText(f"Starting [{self._selectedPreset}] for {len(urls)} item(s)...")

        def worker():
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                assert proc.stdout is not None
                for line in proc.stdout:
                    s = line.strip()
                    if s:
                        self._logLine.emit(s)
                code = proc.wait()
                self._downloadDone.emit(code == 0, f"Finished (exit {code}) -> {outDir}")
            except Exception as e:
                self._downloadDone.emit(False, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _onDownloadDone(self, ok: bool, msg: str) -> None:
        self.yesButton.setEnabled(True)
        self.logOutput.appendPlainText(("✓ " if ok else "✕ ") + msg)


class HashCheckerDialog(MessageBoxBase):
    """Verify local file hashes, open VirusTotal SHA-256 reports, or register expected download hashes."""

    def __init__(self, powerTools=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._powerTools = powerTools
        self._lastSha256 = ""

        self.widget.setFixedWidth(580)
        self.titleLabel = SubtitleLabel("Hash & VirusTotal Verifier", self)
        self.subtitleLabel = CaptionLabel(
            "Verify a downloaded file against an expected hash, check its SHA-256 on VirusTotal, "
            "or pre-register an expected hash for an upcoming download.", self
        )

        fileRow = QHBoxLayout()
        self.fileEdit = LineEdit(self)
        self.fileEdit.setPlaceholderText("Choose a local file OR paste a download URL to auto-verify on complete...")
        self.browseBtn = PushButton("Browse", self)
        fileRow.addWidget(self.fileEdit, 1)
        fileRow.addWidget(self.browseBtn)

        self.expectedEdit = LineEdit(self)
        self.expectedEdit.setPlaceholderText("Expected hash (SHA-256, MD5, SHA-1, or SHA-512 — optional)")

        actionRow = QHBoxLayout()
        self.verifyBtn = PrimaryPushButton("Compute / Verify File", self)
        self.registerBtn = PushButton("Auto-Verify on Complete", self)
        self.vtBtn = PushButton("Open on VirusTotal", self)
        self.vtBtn.setEnabled(False)
        actionRow.addWidget(self.verifyBtn)
        actionRow.addWidget(self.registerBtn)
        actionRow.addWidget(self.vtBtn)

        self.resultLabel = QPlainTextEdit(self)
        self.resultLabel.setReadOnly(True)
        self.resultLabel.setMaximumHeight(110)
        self.resultLabel.setPlaceholderText("Hash verification results will appear here...")

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.subtitleLabel)
        self.viewLayout.addLayout(fileRow)
        self.viewLayout.addWidget(self.expectedEdit)
        self.viewLayout.addLayout(actionRow)
        self.viewLayout.addWidget(self.resultLabel)

        self.yesButton.hide()
        self.cancelButton.setText("Close")

        self.browseBtn.clicked.connect(self._browseFile)
        self.verifyBtn.clicked.connect(self._verifyLocalFile)
        self.registerBtn.clicked.connect(self._registerExpected)
        self.vtBtn.clicked.connect(self._openVirusTotal)

    def _browseFile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Verify", str(cfg.downloadFolder.value))
        if path:
            self.fileEdit.setText(path)

    def _verifyLocalFile(self) -> None:
        path = Path(self.fileEdit.text().strip())
        if not path.is_file():
            self.resultLabel.setPlainText("Select an existing local file to compute its hash.")
            return
        expected = self.expectedEdit.text().strip()
        algo = detectHashAlgorithm(expected) if expected else "sha256"
        actual = computeFileHash(path, algo)
        sha256 = actual if algo == "sha256" else computeFileHash(path, "sha256")
        self._lastSha256 = sha256
        self.vtBtn.setEnabled(True)

        lines = [f"File: {path.name}", f"SHA-256: {sha256}"]
        if algo != "sha256":
            lines.append(f"{algo.upper()}: {actual}")
        if expected:
            target = normalizeHash(expected)
            if actual == target:
                lines.append(f"✓ MATCH — {algo.upper()} matches expected hash.")
            else:
                lines.append(f"✕ MISMATCH — expected {target}")
        self.resultLabel.setPlainText("\n".join(lines))

    def _registerExpected(self) -> None:
        key = self.fileEdit.text().strip()
        expected = self.expectedEdit.text().strip()
        if not key or not expected:
            self.resultLabel.setPlainText("Enter both a download URL/filename and an expected hash.")
            return
        if self._powerTools is not None:
            self._powerTools.registerExpectedHash(key, expected)
            self.resultLabel.setPlainText(
                f"✓ Registered expected {detectHashAlgorithm(expected).upper()} hash for:\n{key}\n"
                "Dodown will automatically verify the file when the download finishes."
            )

    def _openVirusTotal(self) -> None:
        if self._lastSha256:
            QDesktopServices.openUrl(QUrl(virusTotalUrl(self._lastSha256)))


class AutomationRulesDialog(MessageBoxBase):
    """Configure Site-Specific Routing Rules, Auto-Convert Rules, and Quiet Hours schedule."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.widget.setFixedWidth(600)
        self.titleLabel = SubtitleLabel("Automation, Site Rules & Quiet Hours", self)

        # Quiet Hours
        self.quietCheck = CheckBox("Enable Scheduled Quiet Hours (uncap speed automatically overnight)", self)
        self.quietCheck.setChecked(bool(cfg.quietHoursEnabled.value))
        qhRow = QHBoxLayout()
        self.qhStartEdit = LineEdit(self)
        self.qhStartEdit.setText(str(cfg.quietHoursStart.value))
        self.qhStartEdit.setPlaceholderText("00:00")
        self.qhEndEdit = LineEdit(self)
        self.qhEndEdit.setText(str(cfg.quietHoursEnd.value))
        self.qhEndEdit.setPlaceholderText("07:00")
        qhRow.addWidget(BodyLabel("Start (HH:MM):", self))
        qhRow.addWidget(self.qhStartEdit)
        qhRow.addWidget(BodyLabel("End (HH:MM):", self))
        qhRow.addWidget(self.qhEndEdit)

        # Site Rules (one per line: domain = folder | maxThreads)
        self.siteRulesCheck = CheckBox("Enable Site-Specific Routing & Thread Rules", self)
        self.siteRulesCheck.setChecked(bool(cfg.siteRulesEnabled.value))
        self.siteRulesEdit = QPlainTextEdit(self)
        self.siteRulesEdit.setMaximumHeight(110)
        siteLines = [
            f"{r.get('domain', '')} = {r.get('folder', '')} | {r.get('maxThreads', 8)}"
            for r in (cfg.siteRules.value or [])
        ]
        self.siteRulesEdit.setPlainText("\n".join(siteLines))

        # Auto-Convert Rules (one per line: .mkv -> .mp4)
        self.convertCheck = CheckBox("Enable Auto-Convert on Complete (requires FFmpeg)", self)
        self.convertCheck.setChecked(bool(cfg.autoConvertEnabled.value))
        self.convertEdit = QPlainTextEdit(self)
        self.convertEdit.setMaximumHeight(90)
        convLines = [
            f"{r.get('fromExt', '')} -> {r.get('toExt', '')}"
            for r in (cfg.autoConvertRules.value or [])
            if r.get("enabled", True)
        ]
        self.convertEdit.setPlainText("\n".join(convLines))

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.quietCheck)
        self.viewLayout.addLayout(qhRow)
        self.viewLayout.addWidget(self.siteRulesCheck)
        self.viewLayout.addWidget(CaptionLabel("Format: domain = Subfolder | maxThreads (one per line)", self))
        self.viewLayout.addWidget(self.siteRulesEdit)
        self.viewLayout.addWidget(self.convertCheck)
        self.viewLayout.addWidget(CaptionLabel("Format: .mkv -> .mp4 (one per line)", self))
        self.viewLayout.addWidget(self.convertEdit)

        self.yesButton.setText("Save Rules")
        self.cancelButton.setText("Cancel")

    def validate(self) -> bool:
        cfg.set(cfg.quietHoursEnabled, self.quietCheck.isChecked())
        cfg.set(cfg.quietHoursStart, self.qhStartEdit.text().strip() or "00:00")
        cfg.set(cfg.quietHoursEnd, self.qhEndEdit.text().strip() or "07:00")

        cfg.set(cfg.siteRulesEnabled, self.siteRulesCheck.isChecked())
        parsedSiteRules = []
        for line in self.siteRulesEdit.toPlainText().splitlines():
            if "=" not in line:
                continue
            dom, rest = line.split("=", 1)
            if "|" in rest:
                folder, threads = rest.split("|", 1)
                try:
                    tInt = max(1, int(threads.strip()))
                except ValueError:
                    tInt = 8
            else:
                folder, tInt = rest, 8
            if dom.strip():
                parsedSiteRules.append({"domain": dom.strip(), "folder": folder.strip(), "maxThreads": tInt})
        cfg.set(cfg.siteRules, parsedSiteRules)

        cfg.set(cfg.autoConvertEnabled, self.convertCheck.isChecked())
        parsedConvert = []
        for line in self.convertEdit.toPlainText().splitlines():
            if "->" not in line:
                continue
            src, dst = line.split("->", 1)
            src, dst = src.strip(), dst.strip()
            if src and dst:
                parsedConvert.append({"fromExt": src, "toExt": dst, "enabled": True})
        cfg.set(cfg.autoConvertRules, parsedConvert)
        return True
