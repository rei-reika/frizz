#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

# Source virtualenv if exists
if [ -d "$DIR/venv" ]; then
    source "$DIR/venv/bin/activate"
fi

# Ensure ~/.local/bin is in PATH
export PATH="$HOME/.local/bin:$PATH"

if [ ! -f "$DIR/.env" ]; then
    echo "❌ Error: .env file not found in $DIR!"
    echo "Copy .env.example to .env and configure your API_ID and API_HASH."
    exit 1
fi

echo "🚀 Starting FlacDL Telethon MTProto Userbot..."
exec python3 -m bot.main "$@"
