# Dodown

A multi-protocol desktop download manager that splits files into concurrent connections and dynamically redistributes threads to saturate your bandwidth.

**Download page:** [averywsc.github.io/downloader](https://averywsc.github.io/downloader/) · **Portfolio:** [averybeuth.xyz](https://averybeuth.xyz)

## Downloads

- **Windows Installer:** [Dodown-v4.5.11-Windows-Setup.exe](https://github.com/averywsc/downloader/releases/latest/download/Dodown-v4.5.11-Windows-Setup.exe)
- **Windows Portable:** [Dodown-v4.5.11-Windows-x64-Portable.zip](https://github.com/averywsc/downloader/releases/latest/download/Dodown-v4.5.11-Windows-x64-Portable.zip)
- **macOS (arm64):** [Dodown-v4.5.11-macOS-arm64.zip](https://github.com/averywsc/downloader/releases/latest/download/Dodown-v4.5.11-macOS-arm64.zip)
- **Linux (x64):** [Dodown-v4.5.11-Linux-x64.tar.gz](https://github.com/averywsc/downloader/releases/latest/download/Dodown-v4.5.11-Linux-x64.tar.gz)

## What is included

- **Multi-threaded engine:** Dynamic segment splitting with Auto Boost thread redistribution, global speed caps, scheduled Quiet Hours, and resumable transfers.
- **Multi-protocol support:** HTTP/HTTPS, BitTorrent and magnet links via `libtorrent`, M3U8/HLS streams, FTP/FTPS, eD2k, GitHub releases, HuggingFace repositories, and arXiv papers.
- **Media and batch tools:** Built-in `yt-dlp` and `FFmpeg` presets for MP4, MP3, FLAC, and WAV, timestamp clipping, playlist selection, and range-based batch URL generation.
- **Browser and automation:** Custom Manifest V3 browser extension for automatic download capture, Aria2 JSON-RPC support, domain routing rules, auto-extract, auto-convert, and SHA-256 / VirusTotal verification.

## Running from source

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/averywsc/downloader.git
cd downloader
uv sync
uv run python Dodown.py
```

[averybeuth.xyz](https://averybeuth.xyz) · [buymeacoffee.com/averyuwubaka](https://buymeacoffee.com/averyuwubaka)
