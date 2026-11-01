#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "      FlacDL Headless Cloudflare Setup Assistant        "
echo "=========================================================="
echo ""

# Check for lucida binary
LUCIDA_BIN="lucida"
if ! command -v lucida &> /dev/null; then
    if command -v lucidadl &> /dev/null; then
        LUCIDA_BIN="lucidadl"
    elif [ -f "$HOME/.local/bin/lucida" ]; then
        LUCIDA_BIN="$HOME/.local/bin/lucida"
    elif [ -f "$HOME/.local/bin/lucidadl" ]; then
        LUCIDA_BIN="$HOME/.local/bin/lucidadl"
    else
        echo "❌ Error: 'lucida' or 'lucidadl' command not found."
        echo "Please install lucidadl first: pipx install lucidadl"
        exit 1
    fi
fi

echo "Using binary: $LUCIDA_BIN"

# Check if Xvfb is available for headless execution
if command -v xvfb-run &> /dev/null; then
    echo "✅ Found 'xvfb-run'. Launching virtual display session..."
    echo "Running: xvfb-run -a $LUCIDA_BIN setup"
    echo "----------------------------------------------------------"
    xvfb-run -a "$LUCIDA_BIN" setup
    echo "----------------------------------------------------------"
    echo "Testing configuration with doctor..."
    "$LUCIDA_BIN" doctor --live || true
else
    echo "⚠️ 'xvfb-run' is not installed."
    echo "On Debian/Ubuntu, install it with: sudo apt install xvfb"
    echo ""
    echo "Alternatively, perform setup on your local desktop machine:"
    echo "1. Run: pipx install lucidadl && lucida setup"
    echo "2. Copy the resulting directory (~/.local/share/lucidadl)"
    echo "   to this server at: $HOME/.local/share/lucidadl"
fi
