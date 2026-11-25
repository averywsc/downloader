# Dodown

**A fast, multi-protocol desktop download manager built in English with the Totone Studio UI — combining multi-threaded HTTP/HTTPS acceleration, BitTorrent/Magnet, Media & Playlist Studio (`yt-dlp` + `FFmpeg`), M3U8/HLS, FTP, eD2k, GitHub, HuggingFace, and arXiv downloads in one dark-navy studio app.**

[![Website](https://img.shields.io/badge/Website-averybeuth.xyz-091534?style=for-the-badge)](https://averybeuth.xyz)
[![Support](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/averyuwubaka)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13%2B-38bdf8?style=for-the-badge)](#running-locally)

Part of the **Totone / Bebeat / Fifilm** studio suite — more tools at **[averybeuth.xyz](https://averybeuth.xyz)**.

---

## Highlights

- **Totone Studio UI & 8 Theme Presets** — Deep midnight navy (`#050c1f` / `#091534`) by default, with live switching across 8 Totone presets (*Totone Navy, Midnight OLED, Cybercore Lime, Frutiger Aero, Sakura Dusk, Studio Neutral, Warm Film, Paper Light*).
- **Live Speed Sparkline & Status Bar** — Rolling 60-second download speed graph, active/queued/completed counts, free disk space readout, Quiet Hours badge, and 1-click Speed Limit & Floating Drop Pill toggles.
- **Spotlight Command Palette (`Ctrl+K`)** — Search any action, switch themes, toggle automation, or paste a URL straight into `Ctrl+K` to queue it instantly.
- **One-Click Media & Playlist Studio** — Grab *Best MP4*, *Audio MP3*, *Lossless FLAC*, or *Studio WAV* (ready for Bebeat & Fifilm), clip by timestamp (`00:45–01:12`), embed thumbnails/metadata, and batch-pick playlist items with checkboxes.
- **Smart Automation & Security** — Auto-extract archives (`.zip` / `.tar.*`), auto-convert finished files via FFmpeg (`.mkv → .mp4`, `.webm → .mp3`, `.webp → .png`), domain-based routing rules, scheduled Quiet Hours, Batch URL Range Generator (`[01-12]`), Floating Quick-Drop Pill, and built-in Hash & VirusTotal verification.

---

## Feature Breakdown

### Totone Studio UX
- **8 Built-In Studio Themes** — Switch instantly in **Settings → Personalization** or via `Ctrl+K`.
- **Live Speed Sparkline Status Bar** — Real-time bandwidth graph, task counts, disk free space, and instant speed-limit / drop-pill toggles docked at the bottom of the window.
- **Spotlight Command Palette (`Ctrl+K`)** — Keyboard-first command runner and instant URL launcher.
- **Floating Quick-Drop Pill** — Compact, draggable, always-on-top desktop pill displaying live speed and active count; drop links or `.torrent` files onto it without opening the main window.

### Media, Creator & Batch Tools
- **Media & Playlist Studio (`yt-dlp` + `FFmpeg`)** — One-click presets (*Best MP4*, *Audio MP3*, *Lossless FLAC*, *Studio WAV*), timestamp clipping, thumbnail/metadata embedding, and interactive playlist item picker with numbering.
- **Batch URL Range Generator** — Expand range patterns like `https://example.com/ep_[01-12].mp4` or `{mp4,mkv}` with live preview and one-click queuing.

### Smart Automation & Security
- **Auto-Extract & Clean Up** — Automatically unpack `.zip`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, and `.tar.xz` archives into a clean subfolder on completion (with optional archive removal).
- **Auto-Convert on Complete** — Automatically remux or transcode finished files using FFmpeg (e.g., `.mkv → .mp4`, `.webm → .mp3`, `.webp → .png`).
- **Site-Specific Routing & Profiles** — Route downloads by domain (e.g., `github.com → Code`, `huggingface.co → Models`, `youtube.com → Media`) with per-host thread caps.
- **Scheduled Quiet Hours / Night Queue** — Automatically uncap download speed during off-peak hours (default `00:00–07:00`) and restore daytime limits afterward.
- **Hash & VirusTotal Verifier** — Verify local files or pre-register an expected SHA-256 / MD5 / SHA-1 / SHA-512 hash for upcoming downloads, with 1-click VirusTotal SHA-256 lookup.

### Multi-Protocol Engine
- **HTTP / HTTPS** — Multi-segment downloading with Auto Boost thread redistribution, custom header presets, proxy support (`HTTP`, `HTTPS`, `SOCKS4/5`), system DNS, and browser TLS fingerprint profiles.
- **BitTorrent & Magnet** — Powered by `libtorrent` with selective file downloading, DHT, trackers, and seeding limits.
- **Developer, Research & Classic Protocols** — Built-in packs for GitHub releases, HuggingFace repos, arXiv papers, M3U8/HLS streams, FTP/FTPS, eD2k, browser extension WebSocket integration, and Aria2 JSON-RPC compatibility.

---

## Keyboard Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+K` | Open Spotlight Command Palette (commands, themes, or paste URL) |
| `Ctrl+F` | Focus task/settings search bar |

---

## Architecture

```text
downloader/
├── Dodown.py                       # Desktop entry point, single-instance bootstrap, tray & lifecycle
├── pyproject.toml                  # Python 3.13+ dependencies and pytest configuration
├── app/
│   ├── config/                     # Settings (cfg.py), constants, and data/download paths
│   ├── models/                     # Task, pack, and download state models
│   ├── platform/                   # Windows/macOS/Linux integration, notifications, file associations
│   ├── services/
│   │   └── power_tools.py          # Auto-extract, auto-convert, site rules, quiet hours & hash verifier
│   ├── view/
│   │   ├── totone_theme.py         # 8 Totone Studio themes, dynamic QSS & Dodown SVG icon loader
│   │   ├── components/
│   │   │   └── totone_status_bar.py # Live speed sparkline & Totone bottom status bar
│   │   ├── dialogs/
│   │   │   ├── command_palette.py  # Spotlight Command Palette (Ctrl+K)
│   │   │   ├── power_dialogs.py    # Media/Playlist Studio, Hash/VirusTotal & Automation Rules
│   │   │   └── batch_url.py        # Batch URL Range Generator ([01-12], {a,b})
│   │   ├── shell/
│   │   │   └── drop_widget.py      # Always-on-top Floating Quick-Drop Pill
│   │   ├── windows/                # MainWindow & OOBE setup wizard
│   │   └── pages/                  # TaskPage & SettingPage
│   └── assets/                     # Dodown SVG icon (dodown_logo.svg), sounds & file type icons
├── features/                       # Modular protocol packs (http, bittorrent, m3u8, yt_dlp, ftp, ...)
├── browser_extension/              # Companion Chromium/Firefox browser extension
└── tests/                          # Automated test suite
```

---

## Running Locally

Requires **Python 3.13+** (recommended: [uv](https://docs.astral.sh/uv/)).

```bash
git clone https://github.com/averywsc/downloader.git
cd downloader
uv sync
uv run python Dodown.py
```

Or with a standard Python 3.13+ virtual environment:

```bash
pip install -e .
python Dodown.py
```

---

## Inspiration & Open-Source Credits

Dodown takes inspiration from [Ghost Downloader](https://github.com/XiaoYouChR/Ghost-Downloader-3) and the **Totone** studio design language, and is powered by open-source tools including PySide6, PySide6-Fluent-Widgets, `libtorrent`, `wreq`, `aioftp`, `yt-dlp`, and `FFmpeg`.

---

## Links & Support

- **Website**: [averybeuth.xyz](https://averybeuth.xyz)
- **Support**: [buymeacoffee.com/averyuwubaka](https://buymeacoffee.com/averyuwubaka)
