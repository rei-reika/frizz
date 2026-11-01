import shutil
import psutil
from aiogram import Router
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
