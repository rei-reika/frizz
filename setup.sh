#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "          FlacDL Telegram Bot Installer                "
echo "=========================================================="

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Found Python $PY_VER"

# 2. Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment in ./venv..."
    python3 -m venv venv
fi

echo "📦 Installing bot requirements..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 3. Check or install lucidadl via pipx or venv
echo "🔍 Checking lucidadl installation..."
if ! command -v lucida &> /dev/null && ! command -v lucidadl &> /dev/null; then
    echo "Installing lucidadl in virtual environment..."
    ./venv/bin/pip install lucidadl || pipx install lucidadl || true
fi

# 4. Check for ffmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg is installed."
else
    echo "⚠️ Warning: FFmpeg is not found. Audio transcoding / compression fallback requires ffmpeg."
    echo "   Install it with: sudo apt install ffmpeg"
fi

# 5. Check for xvfb
if command -v xvfb-run &> /dev/null; then
    echo "✅ Xvfb is installed."
else
    echo "ℹ️ Note: Xvfb is recommended for running headless Cloudflare setup."
    echo "   Install it with: sudo apt install xvfb"
fi

# 6. Setup .env
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️ Remember to edit .env and insert your BOT_TOKEN from @BotFather!"
else
    echo "✅ Found existing .env file."
fi

# 7. Make scripts executable
chmod +x scripts/*.sh

echo ""
echo "=========================================================="
echo "🎉 Setup Complete!"
echo "Next steps:"
echo "1. Edit .env and set your BOT_TOKEN."
echo "2. Run './scripts/setup_lucida_session.sh' if initial Cloudflare clearance is needed."
echo "3. Start the bot with: './scripts/run_bot.sh'"
echo "=========================================================="
