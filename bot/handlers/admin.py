import shutil
import psutil
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from bot.config import config
from bot.database import db
from bot.services.lucida import lucida_runner
from bot.services import queue_service
from bot.utils.helpers import format_bytes, escape_html

router = Router(name="admin")


@router.message(Command("doctor"))
async def handle_doctor(message: Message):
    """Run lucida doctor to verify dependencies and connection."""
    if not message.from_user or not config.is_admin(message.from_user.id):
        await message.answer("⛔ This command is restricted to administrators.")
        return

    status_msg = await message.answer("🩺 Running <code>lucida doctor --live</code> diagnostics...", parse_mode="HTML")
    report = await lucida_runner.run_doctor(live=True)
    await status_msg.edit_text(
        f"🩺 <b>Lucida Doctor Diagnostic Report:</b>\n\n"
        f"<pre>{escape_html(report)}</pre>",
        parse_mode="HTML"
    )


@router.message(Command("setup_help"))
async def handle_setup_help(message: Message):
    """Instructions for setting up Cloudflare bypass for Lucida."""
    if not message.from_user or not config.is_admin(message.from_user.id):
        await message.answer("⛔ This command is restricted to administrators.")
        return

    help_msg = (
        f"🛠️ <b>Lucida Cloudflare Setup Guide</b>\n\n"
        f"Lucida uses Playwright Chromium to pass Cloudflare bot detection on <code>lucida.to</code> "
        f"and cache access tokens in <code>~/.local/share/lucidadl</code>.\n\n"
        f"<b>Option 1: Setup on Headless Server (using Xvfb)</b>\n"
        f"1. Make sure <code>xvfb</code> is installed on your Linux host:\n"
        f"   <code>sudo apt install xvfb</code>\n"
        f"2. Install Playwright Chromium:\n"
        f"   <code>playwright install chromium</code>\n"
        f"3. Run setup wrapped with xvfb-run:\n"
        f"   <code>xvfb-run -a lucida setup</code>\n\n"
        f"<b>Option 2: Setup on Local Desktop & Copy Session (Most Reliable)</b>\n"
        f"1. On your personal computer (Windows/macOS/Linux Desktop):\n"
        f"   <code>pipx install lucidadl</code>\n"
        f"   <code>lucida setup</code>\n"
        f"2. Complete the Cloudflare prompt in the browser.\n"
        f"3. Copy the session folder to the server:\n"
        f"   • Linux / macOS source: <code>~/.local/share/lucidadl</code>\n"
        f"   • Windows source: <code>%LOCALAPPDATA%\\lucidadl</code>\n"
        f"   • Destination on server: <code>~/.local/share/lucidadl</code>\n"
        f"4. Once copied, Lucida will run headlessly without browser windows!"
    )
    await message.answer(help_msg, parse_mode="HTML")


@router.message(Command("status"))
async def handle_status(message: Message):
    """Display bot stats and server health."""
    # Check permissions if not public
    if message.from_user and not config.is_user_allowed(message.from_user.id):
        return

    # System metrics
    cpu_usage = psutil.cpu_percent(interval=0.2)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # Database metrics
    stats = await db.get_stats()

    # Queue metrics
    active_jobs = len(queue_service.queue_manager.jobs) if queue_service.queue_manager else 0

    text = (
        f"📊 <b>System & Bot Status:</b>\n\n"
        f"<b>🖥️ Server Resources:</b>\n"
        f"• CPU Usage: <code>{cpu_usage}%</code>\n"
        f"• RAM Usage: <code>{ram.percent}% ({format_bytes(ram.used)} / {format_bytes(ram.total)})</code>\n"
        f"• Disk Space: <code>{format_bytes(disk.free)} free / {format_bytes(disk.total)}</code>\n\n"
        f"<b>📥 Download Statistics:</b>\n"
        f"• Total Users: <code>{stats['total_users']}</code>\n"
        f"• Total Downloads: <code>{stats['total_downloads']}</code>\n"
        f"• Successful: <code>{stats['successful_downloads']}</code>\n"
        f"• Audio Files Sent: <code>{stats['total_files_sent']}</code>\n"
        f"• Active / Queued Jobs: <code>{active_jobs}</code>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("broadcast"))
async def handle_broadcast(message: Message):
    """Broadcast announcement to all users."""
    if not message.from_user or not config.is_admin(message.from_user.id):
        await message.answer("⛔ Administrator only.")
        return

    text = ""
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            text = parts[1]

    if not text:
        await message.answer("Usage: <code>/broadcast &lt;announcement message&gt;</code>", parse_mode="HTML")
        return

    user_ids = await db.get_all_user_ids()
    sent = 0
    failed = 0

    status_msg = await message.answer(f"📢 Sending broadcast to {len(user_ids)} users...")

    for uid in user_ids:
        try:
            await message.bot.send_message(
                chat_id=uid,
                text=f"📢 <b>Announcement:</b>\n\n{escape_html(text)}",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"📢 Broadcast finished:\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}"
    )


@router.message(Command("cache"))
async def handle_cache_stats(message: Message):
    """View Telegram file_id cache statistics."""
    if not message.from_user or not config.is_admin(message.from_user.id):
        await message.answer("⛔ Administrator only.")
        return

    stats = await db.get_cache_stats()
    recent_items = await db.list_cached_files(limit=8)

    items_text = ""
    for idx, item in enumerate(recent_items, 1):
        items_text += (
            f"<b>{idx}.</b> <code>{escape_html(item['file_key'])}</code>\n"
            f"   📦 {format_bytes(item['file_size'])} | Hits: <b>{item['access_count']}</b>\n"
        )

    if not items_text:
        items_text = "<i>(No files cached yet)</i>\n"

    report = (
        f"⚡ <b>Telegram file_id Cache Overview:</b>\n\n"
        f"• Total Cached Files: <b>{stats['total_cached_files']}</b>\n"
        f"• Total Stored File Size: <b>{format_bytes(stats['total_cached_size'])}</b>\n"
        f"• Total Cache Hits: <b>{stats['total_cache_hits']}</b>\n"
        f"• Saved Upload Bandwidth: <b>{format_bytes(stats['saved_bandwidth'])}</b>\n\n"
        f"<b>📋 Recently Cached Items:</b>\n"
        f"{items_text}\n"
        f"<i>💡 Tip: Forward or upload any Audio/FLAC up to 2GB to this chat to pre-cache it!</i>"
    )
    await message.answer(report, parse_mode="HTML")


@router.message(Command("delcache"))
async def handle_delcache(message: Message):
    """Delete a cached entry by key."""
    if not message.from_user or not config.is_admin(message.from_user.id):
        await message.answer("⛔ Administrator only.")
        return

    key = ""
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            key = parts[1].strip()

    if not key:
        await message.answer("Usage: <code>/delcache &lt;file_key&gt;</code>", parse_mode="HTML")
        return

    deleted = await db.delete_cached_file(key)
    if deleted:
        await message.answer(f"✅ Cache entry <code>{escape_html(key)}</code> deleted.", parse_mode="HTML")
    else:
        await message.answer(f"⚠️ Cache entry <code>{escape_html(key)}</code> not found.", parse_mode="HTML")


@router.message(F.audio | F.document)
async def handle_admin_file_upload(message: Message):
    """
    Allow admins to manually upload/forward large files (up to 2GB via Telegram)
    to pre-cache their file_id and bypass the 50MB Bot API upload limit.
    """
    if not message.from_user or not config.is_admin(message.from_user.id):
        return

    caption_key = message.caption.strip() if message.caption else ""
    file_id = ""
    file_unique_id = ""
    file_name = ""
    file_size = 0
    media_type = "audio"
    title = ""
    performer = ""
    duration = 0

    if message.audio:
        media_type = "audio"
        audio = message.audio
        file_id = audio.file_id
        file_unique_id = audio.file_unique_id
        file_size = audio.file_size or 0
        file_name = audio.file_name or "track.flac"
        title = audio.title or file_name
        performer = audio.performer or "Unknown Artist"
        duration = audio.duration or 0

    elif message.document:
        media_type = "document"
        doc = message.document
        file_id = doc.file_id
        file_unique_id = doc.file_unique_id
        file_size = doc.file_size or 0
        file_name = doc.file_name or "file.bin"
        title = file_name
        performer = "Document Attachment"

    # Determine cache key:
    # 1. Custom key from caption if provided by admin
    # 2. Or standard "Artist - Title.ext" if available
    # 3. Or original file_name
    primary_key = caption_key if caption_key else file_name
    if not primary_key and performer and title:
        primary_key = f"{performer} - {title}.flac"

    # Save to database cache
    await db.save_cached_file(
        file_key=primary_key,
        file_id=file_id,
        file_unique_id=file_unique_id,
        file_name=file_name,
        file_size=file_size,
        media_type=media_type,
        title=title,
        performer=performer,
        duration=duration
    )

    # Also save normalized filename key if different
    if file_name and file_name.lower() != primary_key.lower():
        await db.save_cached_file(
            file_key=file_name,
            file_id=file_id,
            file_unique_id=file_unique_id,
            file_name=file_name,
            file_size=file_size,
            media_type=media_type,
            title=title,
            performer=performer,
            duration=duration
        )

    # Also save performer - title alias if applicable
    if performer and title and performer != "Unknown Artist":
        artist_title_key = f"{performer} - {title}".lower()
        await db.save_cached_file(
            file_key=artist_title_key,
            file_id=file_id,
            file_unique_id=file_unique_id,
            file_name=file_name,
            file_size=file_size,
            media_type=media_type,
            title=title,
            performer=performer,
            duration=duration
        )

    await message.reply(
        f"⚡ <b>File Cached Successfully in Telegram Cloud!</b>\n\n"
        f"🔑 <b>Primary Key:</b> <code>{escape_html(primary_key)}</code>\n"
        f"🆔 <b>file_id:</b> <code>{file_id[:35]}...</code>\n"
        f"📦 <b>Size:</b> {format_bytes(file_size)}\n"
        f"🎵 <b>Title:</b> {escape_html(title)}\n"
        f"👤 <b>Artist:</b> {escape_html(performer)}\n"
        f"📁 <b>Type:</b> <code>{media_type}</code>\n\n"
        f"<i>✅ Users requesting this song or key will now receive it instantly via Telegram's cloud, "
        f"bypassing downloading and bypassing the 50MB upload limit!</i>",
        parse_mode="HTML"
    )

