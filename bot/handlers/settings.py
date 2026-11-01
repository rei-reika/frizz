from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from bot.database import db
from bot.config import config
from bot.keyboards import (
    get_settings_main_keyboard,
    get_format_keyboard,
    get_bitrate_keyboard,
    get_service_keyboard,
    get_send_as_keyboard
)

router = Router(name="settings")


def format_settings_text(settings: dict) -> str:
    fmt = settings.get("audio_format", "flac").upper()
    rate = settings.get("bitrate", "320k")
    srv = settings.get("service", "default").capitalize()
    send_as = "Native Audio Player" if settings.get("send_as", "audio") == "audio" else "Document / File"

    return (
        f"⚙️ <b>Your FlacDL Preferences:</b>\n\n"
        f"• <b>Audio Format:</b> <code>{fmt}</code>\n"
        f"• <b>Bitrate (for lossy):</b> <code>{rate}</code>\n"
        f"• <b>Service Provider:</b> <code>{srv}</code>\n"
        f"• <b>Delivery Mode:</b> <code>{send_as}</code>\n\n"
        f"<i>Tap any button below to customize your settings:</i>"
    )


@router.message(Command("settings"))
async def handle_settings_command(message: Message):
    if not message.from_user:
        return
    user_settings = await db.get_user_settings(message.from_user.id)
    text = format_settings_text(user_settings)
    kb = get_settings_main_keyboard(user_settings)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "menu:main")
async def handle_menu_main(callback: CallbackQuery):
    if not callback.from_user or not callback.message:
        return
    user_settings = await db.get_user_settings(callback.from_user.id)
    text = format_settings_text(user_settings)
    kb = get_settings_main_keyboard(user_settings)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu:format")
async def handle_menu_format(callback: CallbackQuery):
    if not callback.from_user or not callback.message:
        return
    user_settings = await db.get_user_settings(callback.from_user.id)
    kb = get_format_keyboard(user_settings.get("audio_format", "flac"))
    await callback.message.edit_text(
        "🎵 <b>Select Output Audio Format:</b>\n\n"
        "• <b>FLAC:</b> Lossless studio master quality (recommended)\n"
        "• <b>MP3:</b> Universal compatibility, 320kbps\n"
        "• <b>AAC / M4A:</b> Optimal for Apple devices\n"
        "• <b>OPUS:</b> High quality at smaller file sizes\n"
        "• <b>WAV:</b> Uncompressed PCM audio",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "menu:bitrate")
async def handle_menu_bitrate(callback: CallbackQuery):
    if not callback.from_user or not callback.message:
        return
    user_settings = await db.get_user_settings(callback.from_user.id)
    kb = get_bitrate_keyboard(user_settings.get("bitrate", "320k"))
    await callback.message.edit_text(
        "⚡ <b>Select Transcoding Bitrate:</b>\n"
        "<i>(Applies when converting to lossy formats like MP3, AAC, OPUS, OGG)</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "menu:service")
async def handle_menu_service(callback: CallbackQuery):
    if not callback.from_user or not callback.message:
        return
    user_settings = await db.get_user_settings(callback.from_user.id)
    kb = get_service_keyboard(user_settings.get("service", "default"))
    await callback.message.edit_text(
        "🌐 <b>Select Streaming Source Provider:</b>\n\n"
        "• <b>Default / Automatic:</b> Let Lucida pick the best lossless source\n"
        "• <b>Qobuz:</b> Lossless 16-bit and 24-bit Hi-Res master tracks\n"
        "• <b>Amazon:</b> Amazon Music HD / Ultra HD\n"
        "• <b>GrilledCheese:</b> Lucida backup stream provider",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "menu:send_as")
async def handle_menu_send_as(callback: CallbackQuery):
    if not callback.from_user or not callback.message:
        return
    user_settings = await db.get_user_settings(callback.from_user.id)
    kb = get_send_as_keyboard(user_settings.get("send_as", "audio"))
    await callback.message.edit_text(
        "📦 <b>Select Delivery Mode:</b>\n\n"
        "• <b>Native Audio:</b> Plays in Telegram's built-in music player with artwork and artist tags.\n"
        "• <b>Document / File:</b> Sent as a raw uncompressed file attachment.",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set:"))
async def handle_set_setting(callback: CallbackQuery):
    if not callback.from_user or not callback.message or not callback.data:
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        return
    _, key, val = parts
    await db.update_user_setting(callback.from_user.id, key, val)
    user_settings = await db.get_user_settings(callback.from_user.id)

    # Return to updated main menu
    text = format_settings_text(user_settings)
    kb = get_settings_main_keyboard(user_settings)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer(f"Updated {key} to {val}!")


@router.callback_query(F.data == "settings:reset")
async def handle_settings_reset(callback: CallbackQuery):
    if not callback.from_user or not callback.message:
        return
    await db.update_user_setting(callback.from_user.id, "audio_format", config.DEFAULT_FORMAT)
    await db.update_user_setting(callback.from_user.id, "bitrate", config.DEFAULT_BITRATE)
    await db.update_user_setting(callback.from_user.id, "service", config.DEFAULT_SERVICE)
    await db.update_user_setting(callback.from_user.id, "send_as", "audio")

    user_settings = await db.get_user_settings(callback.from_user.id)
    text = format_settings_text(user_settings)
    kb = get_settings_main_keyboard(user_settings)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer("Settings reset to defaults!")


@router.callback_query(F.data == "settings:close")
async def handle_settings_close(callback: CallbackQuery):
    if callback.message:
        await callback.message.delete()
    await callback.answer()
