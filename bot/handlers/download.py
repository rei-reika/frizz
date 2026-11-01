from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from bot.database import db
from bot.keyboards import get_cancel_keyboard
from bot.services import queue_service
from bot.utils.url_parser import MusicResourceParser
from bot.utils.helpers import escape_html

router = Router(name="download")


async def _enqueue_download(message: Message, command_type: str, target: str):
    """Helper to register and queue a download job."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    target = target.strip()

    if not target:
        await message.answer(
            f"⚠️ Please provide a song name or streaming link.\n"
            f"Example: <code>/{command_type} Adele - Easy On Me</code> or paste a Spotify/Apple link.",
            parse_mode="HTML"
        )
        return

    # Fetch user's saved preferences
    settings = await db.get_user_settings(user_id)
    fmt = settings.get("audio_format", "flac").upper()
    srv = settings.get("service", "default").capitalize()

    # Send initial status message
    status_msg = await message.answer(
        f"⏳ <b>Queued for Download:</b>\n"
        f"🎯 <code>{escape_html(target)}</code>\n"
        f"📦 Type: <b>{command_type.capitalize()}</b>\n"
        f"🎵 Format: <b>{fmt}</b> | 🌐 Service: <b>{srv}</b>\n\n"
        f"<i>Waiting for an available download slot...</i>",
        parse_mode="HTML"
    )

    if queue_service.queue_manager is None:
        await status_msg.edit_text("❌ Download queue is not initialized. Contact bot administrator.")
        return

    job = await queue_service.queue_manager.submit_job(
        user_id=user_id,
        chat_id=chat_id,
        command_type=command_type,
        target=target,
        settings=settings,
        status_message_id=status_msg.message_id
    )

    # Attach cancel button with job ID
    cancel_kb = get_cancel_keyboard(job.job_id)
    pos = queue_service.queue_manager.get_queue_position(job.job_id)
    pos_text = f" (Position in queue: {pos})" if pos > 0 else ""

    await status_msg.edit_reply_markup(reply_markup=cancel_kb)


@router.message(Command("track"))
async def handle_track_command(message: Message):
    target = ""
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            target = parts[1]
    await _enqueue_download(message, "track", target)


@router.message(Command("album"))
async def handle_album_command(message: Message):
    target = ""
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            target = parts[1]
    await _enqueue_download(message, "album", target)


@router.message(Command("playlist"))
async def handle_playlist_command(message: Message):
    target = ""
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            target = parts[1]
    await _enqueue_download(message, "playlist", target)


@router.callback_query(F.data.startswith("cancel_job:"))
async def handle_cancel_job(callback: CallbackQuery):
    if not callback.data:
        return
    job_id = callback.data.split(":", 1)[1]
    if queue_service.queue_manager is None:
        await callback.answer("Queue manager not running.")
        return

    success = queue_service.queue_manager.cancel_job(job_id)
    if success:
        await callback.answer("Download cancelled.")
        if callback.message:
            await callback.message.edit_text("❌ Download was cancelled by user.", reply_markup=None)
    else:
        await callback.answer("Job already finished or not found.", show_alert=True)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_direct_text(message: Message):
    """Handle direct text input: auto-detect link type or search query."""
    if not message.text or not message.from_user:
        return

    text = message.text.strip()
    command_type, target = MusicResourceParser.detect_type(text)
    await _enqueue_download(message, command_type, target)
