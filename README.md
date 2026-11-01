# ⚡ FlacDL Telethon MTProto Userbot (Google Cloud Shell)

A high-performance **Telethon-based Telegram Userbot** designed to bypass the standard Bot API 50 MB limitation by streaming large files (up to **2 GB**) directly from **Google Cloud Shell** storage using Telegram's native **MTProto protocol**.

Integrated with **LucidaDL** to fetch lossless master audio (FLAC, Hi-Res) from **Spotify, Apple Music, Deezer, TIDAL, Qobuz, SoundCloud, and Amazon Music**.

---

## 🌟 Key Features

- **🚀 2 GB Direct MTProto Uploads (Bypassing 50 MB Limit):**
  - Unlike standard Bot API bots (which strictly enforce a 50 MB upload limit from disk), this userbot connects as a client via MTProto and can upload files up to **2,000 MB (2 GB)** directly.
- **💾 Persistent Login Session in Google Cloud Shell:**
  - Google Cloud Shell only preserves files located inside `$HOME`. Any files in `/tmp` or system directories are erased on restart.
  - The login session is explicitly pinned to **`$HOME/.telethon_sessions/flacdl_userbot.session`** so you never get logged out automatically when Cloud Shell restarts or goes idle.
- **📊 Interactive Terminal Progress Bar (`rich`):**
  - Live visual progress bar in the terminal with transfer speed (`MB/s`), uploaded/total size, percentage, and estimated time remaining (ETA).
- **🎶 Full Music Downloader (`lucidadl`):**
  - Handles single tracks, full albums, and streaming playlists.
  - Automatically embeds track title, artist, album, duration, and album cover art thumbnail using `DocumentAttributeAudio`.
- **💻 CLI Direct Upload Mode:**
  - Quickly upload any large file on your Google Cloud Shell disk directly to your "Saved Messages" or a chat straight from the terminal.

---

## 🛠️ Requirements & Installation

### 1. Telegram API Credentials
You need an **API ID** and **API HASH** (not a bot token).
1. Log in to [https://my.telegram.org](https://my.telegram.org) with your phone number.
2. Go to **API development tools**.
3. Create an application (any name/short name) and copy your `API_ID` and `API_HASH`.

### 2. Setup on Google Cloud Shell
Run the setup script or install dependencies:
```bash
cd ~/t-server
source venv/bin/activate
pip install -r requirements.txt
pip install lucidadl playwright
```

### 3. Configure `.env`
```bash
cp .env.example .env
nano .env
```
Fill in your credentials:
```ini
API_ID=12345678
API_HASH=0123456789abcdef0123456789abcdef
```

---

## 🚀 Running the Userbot

### First-Time Interactive Login
Start the userbot using the runner script:
```bash
./scripts/run_bot.sh
```
1. You will be prompted in the terminal for your **Phone number** (with country code, e.g. `+628123456789`).
2. Telegram will send a verification code to your Telegram app. Enter the code in the terminal.
3. If you have Two-Step Verification (2FA) enabled, enter your password.
4. **Session saved!** The session file is safely written to `$HOME/.telethon_sessions/flacdl_userbot.session` and will persist indefinitely.

---

## 💬 Userbot Commands

Send these commands from your Telegram account in **Saved Messages** or any chat:

| Command | Description |
| :--- | :--- |
| `.flac <song or link>` | Download track/album/playlist and stream up to 2GB via MTProto |
| `.dl <song or link>` | Alias for `.flac` |
| `.upload <filepath>` | Directly upload any file sitting on Google Cloud Shell storage |
| `.status` | Display Google Cloud Shell CPU, RAM, disk space, and MTProto info |
| `.doctor` | Run LucidaDL diagnostic checks |
| `.help` | Show command guide |

> **Direct Link Support:** You can simply paste any Spotify, Apple Music, Deezer, Tidal, or Qobuz link directly into **Saved Messages**!

---

## 💻 Terminal CLI Direct Upload

You can also upload any large file from your Google Cloud Shell storage directly from the terminal without using the chat:

```bash
# Upload to your Saved Messages:
./scripts/run_bot.sh upload /path/to/large_audio.flac

# Upload to a specific chat / user / channel:
./scripts/run_bot.sh upload /path/to/large_album.zip @username_or_channel
```

---

## 📁 Project Architecture

```
t-server/
├── bot/
│   ├── config.py              # Settings & persistent $HOME session path logic
│   ├── main.py                # Telethon client lifecycle, CLI mode & runner
│   ├── handlers/
│   │   └── userbot_handlers.py# Userbot event listeners (.flac, .upload, .status)
│   ├── services/
│   │   ├── telethon_client.py # TelegramClient setup & interactive terminal login
│   │   ├── uploader.py        # client.send_file() with rich terminal progress bar
│   │   ├── audio_metadata.py  # Mutagen tags & thumbnail extractor
│   │   └── lucida.py          # Asynchronous lucidadl execution
│   └── utils/
│       ├── url_parser.py      # Music URL classifier (Spotify, Apple, Qobuz, etc.)
│       └── helpers.py         # Formatters, human-readable byte sizes
├── scripts/
│   ├── run_bot.sh             # Launch script
│   └── setup_lucida_session.sh# Headless Cloudflare clearance helper
├── requirements.txt           # Telethon, rich, cryptg, mutagen, etc.
├── .env.example               # Configuration template
└── README.md                  # Complete documentation
```
