# 🎵 FlacDL Telegram Bot

A production-grade, asynchronous Telegram Bot designed to download lossless (FLAC) and high-bitrate music.

Supports seamless single-track downloads, full albums, and entire public streaming playlists from **Spotify, Apple Music, Deezer, TIDAL, Qobuz, SoundCloud, Amazon Music, and YouTube Music**.

---

## ✨ Features

- **🎧 Universal Music Downloader:**
  - Auto-detects tracks, albums, and playlists from shared URLs.
  - Supports raw search queries (e.g., `Adele - Easy On Me`).
  - Fetches from top lossless sources (Qobuz 24-bit Hi-Res, Amazon Music HD, etc.).
- **🎛️ Interactive In-Chat Settings (`/settings`):**
  - Choose output audio format: `FLAC (Lossless)`, `MP3 (320k)`, `AAC / M4A`, `OPUS`, `OGG`, `WAV`.
  - Transcoding bitrate selection: `320k`, `256k`, `192k`, `128k`.
  - Streaming provider selection: `Default (Auto)`, `Qobuz`, `Amazon Music`, `GrilledCheese`.
  - Delivery mode: Native Telegram Audio Player (with cover art) or Raw Document.
- **🎨 Rich Metadata & Artwork:**
  - Extracts and embeds track title, artist, album name, track duration, and album cover art thumbnail into Telegram's native player.
- **⚡ Async Concurrency & Queue Manager:**
  - Prevents server overload with configurable worker pool (`MAX_CONCURRENT_DOWNLOADS`).
  - Real-time download progress updates and debounced status editing.
  - In-chat cancellation button (`[ ❌ Cancel ]`) for active or queued downloads.
- **📦 Smart Telegram Upload Handling:**
  - Telegram Cloud Bot API restricts file uploads to **50MB**. If a lossless FLAC exceeds 50MB, the bot automatically compresses it to a pristine 320kbps MP3 so you never miss a track.
  - Supports **Local Telegram Bot API Server** (`LOCAL_BOT_API_URL`) for up to **2GB** per audio file!
- **🛡️ Access Control & Admin Tools:**
  - Whitelist mode (`ALLOWED_USERS`) to keep the bot private, or open to all.
  - `/doctor` command: Runs diagnostic self-checks.
  - `/status` command: Real-time system resources (CPU, RAM, Disk) and download counters.
  - `/setup_help`: Step-by-step guidance for Cloudflare clearance.
  - Automatic temp directory cleanup after files are uploaded.

---

## 🚀 Quick Start (Native Linux / VPS)

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.12 & 3.13)
- **FFmpeg** (for metadata and compression fallback):
  ```bash
  sudo apt update && sudo apt install -y ffmpeg xvfb
  ```

### 2. Install Dependencies
Run the automated setup script:
```bash
./setup.sh
```

### 3. Configure `.env`
Copy the example environment configuration:
```bash
cp .env.example .env
nano .env
```
Set your `BOT_TOKEN` obtained from [@BotFather](https://t.me/BotFather):
```ini
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
ALLOWED_USERS=              # Optional: your Telegram user ID
ADMIN_IDS=                  # Optional: your Telegram user ID
```

### 4. Launch the Bot
```bash
./scripts/run_bot.sh
```

---

## 🐳 Docker Deployment

You can deploy the entire stack using Docker Compose:

```bash
# 1. Edit .env with your BOT_TOKEN
cp .env.example .env
nano .env

# 2. Build and start container
docker compose up -d --build

# 3. View logs
docker compose logs -f
```

---

## ⚙️ Running as a Systemd Service

To keep the bot running 24/7 in the background and start automatically on boot:

1. Verify paths and user in `flacdl.service`.
2. Install and enable the service:
```bash
sudo cp flacdl.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flacdl
```
3. Check service status:
```bash
sudo systemctl status flacdl
journalctl -u flacdl -f
```

---

## 💬 Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | Launch the bot and view introduction |
| `/track <query or link>` | Download a single audio track |
| `/album <query or link>` | Download an entire album |
| `/playlist <link>` | Download an entire public streaming playlist |
| `/settings` | Open interactive format, bitrate, and provider selector |
| `/status` | View server CPU, RAM, disk space, and bot download statistics |
| `/help` | Detailed help and supported music services |
| `/doctor` *(Admin)* | Run `lucida doctor --live` connection diagnostics |
| `/setup_help` *(Admin)* | View Cloudflare clearance instructions |
| `/broadcast <msg>` *(Admin)* | Send an announcement to all users in the database |

> **Tip:** You do not need to type `/track` or `/album`. Simply sending a Spotify or Apple Music link directly into the chat will automatically detect the type and start downloading!

---

## 📁 Project Architecture

```
t-server/
├── bot/
│   ├── config.py              # Environment configuration & access control
│   ├── database.py            # SQLite database (settings & statistics)
│   ├── keyboards.py           # Interactive inline keyboards (settings & cancel)
│   ├── main.py                # Bot lifecycle, polling & command menus
│   ├── handlers/
│   │   ├── common.py          # /start, /help, /about
│   │   ├── download.py        # /track, /album, /playlist, link detection
│   │   ├── settings.py        # /settings inline interactive menu
│   │   └── admin.py           # /doctor, /status, /setup_help, /broadcast
│   ├── middlewares/
│   │   └── auth.py            # User ID whitelist & access control
│   ├── services/
│   │   ├── lucida.py          # Asynchronous lucidadl execution & progress parsing
│   │   ├── queue_service.py   # Concurrency-limited worker queue
│   │   ├── audio_metadata.py  # Mutagen tags & cover art extractor
│   │   └── uploader.py        # Telegram file sender (size limits & album handling)
│   └── utils/
│       ├── url_parser.py      # Music provider URL & type classifier
│       └── helpers.py         # Formatters, progress bar, directory cleanup
├── scripts/
│   ├── run_bot.sh             # Bot launch script
│   └── setup_lucida_session.sh# Headless Cloudflare clearance helper
├── Dockerfile                 # Production container build
├── docker-compose.yml         # Container orchestration (service: flacdl)
├── requirements.txt           # Python dependencies
├── .env.example               # Configuration template
├── flacdl.service             # Linux systemd daemon unit
└── setup.sh                   # One-click installation script
```

---

## 📄 License
This project is open-source under the MIT License.
