from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict, Any


def get_cancel_keyboard(job_id: str) -> InlineKeyboardMarkup:
    """Keyboard containing a cancel button for an active download job."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Cancel Download",
                    callback_data=f"cancel_job:{job_id}"
                )
            ]
        ]
    )


def get_settings_main_keyboard(current_settings: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Main settings menu keyboard."""
    fmt = current_settings.get("audio_format", "flac").upper()
    rate = current_settings.get("bitrate", "320k")
    srv = current_settings.get("service", "default").capitalize()
    send_as = current_settings.get("send_as", "audio").capitalize()

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🎵 Format: {fmt}",
                    callback_data="menu:format"
                ),
                InlineKeyboardButton(
                    text=f"⚡ Bitrate: {rate}",
                    callback_data="menu:bitrate"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🌐 Service: {srv}",
                    callback_data="menu:service"
                ),
                InlineKeyboardButton(
                    text=f"📦 Send As: {send_as}",
                    callback_data="menu:send_as"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Reset to Defaults",
                    callback_data="settings:reset"
                ),
                InlineKeyboardButton(
                    text="❌ Close",
                    callback_data="settings:close"
                )
            ]
        ]
    )


def get_format_keyboard(current_format: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting audio output format."""
    formats = [
        ("FLAC (Lossless)", "flac"),
        ("MP3 (Universal)", "mp3"),
        ("AAC / M4A (Apple)", "m4a"),
        ("OPUS (Efficient)", "opus"),
        ("OGG (Vorbis)", "ogg"),
        ("WAV (Uncompressed)", "wav")
    ]
    rows = []
    for label, val in formats:
        check = " ✅" if val == current_format else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{label}{check}",
                callback_data=f"set:audio_format:{val}"
            )
        ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Back", callback_data="menu:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_bitrate_keyboard(current_bitrate: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting lossy audio bitrate."""
    bitrates = ["320k", "256k", "192k", "128k"]
    row = []
    for br in bitrates:
        check = " ✅" if br == current_bitrate else ""
        row.append(
            InlineKeyboardButton(
                text=f"{br}{check}",
                callback_data=f"set:bitrate:{br}"
            )
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row,
            [InlineKeyboardButton(text="⬅️ Back", callback_data="menu:main")]
        ]
    )


def get_service_keyboard(current_service: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting streaming provider."""
    services = [
        ("Automatic / Default", "default"),
        ("Qobuz (Lossless)", "qobuz"),
        ("Amazon Music", "amazon"),
        ("GrilledCheese", "grilledcheese")
    ]
    rows = []
    for label, val in services:
        check = " ✅" if val == current_service else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{label}{check}",
                callback_data=f"set:service:{val}"
            )
        ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Back", callback_data="menu:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_send_as_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting whether files are sent as native Audio or Document."""
    modes = [
        ("Native Audio Player (with Album Art)", "audio"),
        ("Document / File (Original metadata)", "document")
    ]
    rows = []
    for label, val in modes:
        check = " ✅" if val == current_mode else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{label}{check}",
                callback_data=f"set:send_as:{val}"
            )
        ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Back", callback_data="menu:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
