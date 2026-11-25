# Dodown

**A fast, multi-protocol desktop download manager built in English with the Totone Studio UI — combining multi-threaded HTTP/HTTPS acceleration, BitTorrent/Magnet, yt-dlp, M3U8/HLS, FTP, eD2k, GitHub, HuggingFace, and arXiv downloads in one clean, dark-navy desktop app.**

[![Website](https://img.shields.io/badge/Website-averybeuth.xyz-091534?style=for-the-badge)](https://averybeuth.xyz)
[![Support](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/averyuwubaka)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13%2B-38bdf8?style=for-the-badge)](#running-locally)

Part of the **Totone / Bebeat / Fifilm** studio suite — more tools at **[averybeuth.xyz](https://averybeuth.xyz)**.

---

## Highlights

- **Totone Studio UI** — Deep midnight navy (`#050c1f` / `#091534`), crisp 1px slate-blue borders (`#16254d` / `#34477e`), high-contrast pure white accents (`#ffffff`), flat chrome, slim dock navigation, and clean tabular speed/ETA readouts.
- **Multi-Threaded & Auto-Boost Engine** — Splits downloads across concurrent segments and dynamically redistributes threads to saturate your connection without manual tweaking.
- **Multi-Protocol Feature Packs** — Out-of-the-box support for HTTP/HTTPS, BitTorrent & Magnet links, M3U8/HLS streams, FTP/FTPS, eD2k, YouTube & media sites (`yt-dlp`), GitHub releases, HuggingFace repos, arXiv papers, FFmpeg media tools, and automatic ZIP extraction.
- **Browser Extension & Aria2 RPC** — Intercept browser downloads directly or send tasks from any Aria2-compatible tool or userscript.
- **100% Native English** — Every window, setting, dialog, notification, error message, and CLI command is written in English.

---

## Feature Breakdown

### Download Engine & Queue
- **Dynamic Thread Redistribution (Auto Boost)** — Monitors per-thread speed and automatically reallocates segments when threads finish early.
- **Global Speed Limiter & Scheduling** — Toggle speed caps from the toolbar, queue concurrent tasks, and run post-completion actions (sleep, shutdown, or custom plan).
- **Smart File Handling** — Automatic file categorization by type (Videos, Audio, Documents, Archives, etc.), duplicate filename conflict handling (`Keep Both`, `Overwrite`, `Ask`), checksum verification (`MD5`, `SHA-1`, `SHA-256`, `SHA-512`), and `Last-Modified` timestamp preservation.
- **Clipboard & Drag-and-Drop** — Automatically detect copied download links or drop URLs, `.torrent`, and `.m3u8` files straight onto the window.

### Built-In Feature Packs
- **HTTP / HTTPS** — Multi-segment downloading with custom headers presets, proxy support (`HTTP`, `HTTPS`, `SOCKS4/5`), system DNS, and browser TLS fingerprint profiles.
- **BitTorrent & Magnet** — Powered by `libtorrent` with selective file downloading, DHT, tracker lists, and seeding ratio/time limits.
- **Media & Streams (`yt-dlp`, `M3U8`, `FFmpeg`)** — Download streaming video/audio, HLS playlists with subtitles, and clip/mux media via FFmpeg.
- **Developer & Research (`GitHub`, `HuggingFace`, `arXiv`)** — Download release assets, model repositories, and papers named automatically by title (with optional TeX source & BibTeX).
- **Classic Protocols (`FTP`, `eD2k`, `ZIP`)** — Full FTP/SFTP directory & file support, eD2k links, and archive inspection/extraction.

### Automation & CLI
- **Single-Instance CLI (`dodown`)** — Add URLs, inspect status, or launch silently in the background (`--silence`).
- **URL Scheme (`dodown://`) & File Associations** — Register `.torrent`, `.m3u8`, `magnet:`, `ed2k:`, and `ftp:` links to open directly in Dodown.

---

## Architecture

```text
downloader/
├── Dodown.py                 # Desktop entry point, single-instance bootstrap, tray & lifecycle
├── pyproject.toml            # Python 3.13+ dependencies and pytest configuration
├── app/
│   ├── config/               # Settings (cfg.py), constants, and data/download paths
│   ├── models/               # Task, pack, and download state models
│   ├── platform/             # Windows/macOS/Linux integration, notifications, file associations
│   ├── services/             # Task queue, browser extension WebSocket, Aria2 RPC, speed meter
│   ├── view/
│   │   ├── totone_theme.py   # Totone Studio navy palette, QSS stylesheet & Dodown icon loader
│   │   ├── windows/          # MainWindow & OOBE setup wizard
│   │   ├── pages/            # TaskPage & SettingPage
│   │   ├── cards/            # Task cards & draft cards
│   │   ├── components/       # Toolbar, editors, setting cards, progress toast, banners
│   │   └── dialogs/          # Task draft, batch URL, file/subtitle select, presets
│   └── assets/               # Dodown SVG icon (dodown_logo.svg), sounds & file type icons
├── features/                 # Modular protocol packs (http, bittorrent, m3u8, yt_dlp, ftp, ...)
├── browser_extension/        # Companion Chromium/Firefox browser extension
└── tests/                    # Automated test suite
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

## Credits

Dodown is adapted and restyled in English from the open-source [Ghost-Downloader-3](https://github.com/XiaoYouChR/Ghost-Downloader-3) engine, powered by PySide6, PySide6-Fluent-Widgets, `libtorrent`, `wreq`, `aioftp`, `yt-dlp`, and `FFmpeg`.

---

## Links & Support

- **Website**: [averybeuth.xyz](https://averybeuth.xyz)
- **Support**: [buymeacoffee.com/averyuwubaka](https://buymeacoffee.com/averyuwubaka)
