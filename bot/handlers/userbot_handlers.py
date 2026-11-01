import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional

from telethon import TelegramClient, events
from telethon.tl.custom import Message
from rich.console import Console

from bot.config import config
from bot.services.uploader import TelethonUploader
from bot.services.lucida import lucida_runner
from bot.utils.url_parser import MusicResourceParser
from bot.utils.helpers import format_bytes, format_duration, safe_remove_directory

console = Console()


def register_userbot_handlers(client: TelegramClient):
    uploader = TelethonUploader(client)

    @client.on(events.NewMessage)
    async def message_dispatcher(event: Message):
        text = event.raw_text.strip() if event.raw_text else ""
        if not text:
            return

        sender = await event.get_sender()
        sender_id = sender.id if sender else 0
        me = await client.get_me()
        my_id = me.id

        # Access check
        if not config.is_user_allowed(sender_id, my_id):
            return

        prefix = config.COMMAND_PREFIX

        # Check for commands or raw streaming links
        if text.startswith(f"{prefix}help") or text.startswith("/help"):
            await handle_help(event)
        elif text.startswith(f"{prefix}status") or text.startswith("/status"):
            await handle_status(event, my_id)
        elif text.startswith(f"{prefix}doctor") or text.startswith("/doctor"):
            await handle_doctor(event)
        elif text.startswith(f"{prefix}upload") or text.startswith("/upload"):
            await handle_upload_cmd(event, uploader)
        elif text.startswith(f"{prefix}dl") or text.startswith(f"{prefix}flac") or text.startswith("/dl") or text.startswith("/flac"):
            await handle_download_cmd(event, uploader)
        elif MusicResourceParser.is_url(text):
            # Auto-detect if raw URL is sent
            await handle_direct_url(event, text, uploader)

    async def handle_help(event: Message):
        p = config.COMMAND_PREFIX
        help_text = (
            f"⚡ **FlacDL Telethon MTProto Userbot**\n"
            f"Direct large file streaming from Google Cloud Shell (up to 2GB).\n\n"
            f"**Commands:**\n"
            f"• `{p}flac <query or link>` — Download & upload lossless music\n"
            f"• `{p}dl <query or link>` — Alias for downloading\n"
            f"• `{p}upload <filepath>` — Upload any file from Cloud Shell disk directly\n"
            f"• `{p}status` — Server resources, disk space, and MTProto info\n"
            f"• `{p}doctor` — LucidaDL diagnostic check\n"
            f"• `{p}help` — View this guide\n\n"
            f"💡 *Tip:* You can also simply paste any Spotify, Apple, Qobuz, or Tidal link."
        )
        await event.reply(help_text)

    async def handle_status(event: Message, my_id: int):
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(str(Path.home()))

        status_text = (
            f"📊 **Google Cloud Shell & Userbot Status:**\n\n"
            f"• **Session Target:** `{config.session_file_path}.session` (Persistent $HOME)\n"
            f"• **CPU Load:** `{cpu}%`\n"
            f"• **RAM Usage:** `{ram.percent}% ({format_bytes(ram.used)} / {format_bytes(ram.total)})`\n"
            f"• **$HOME Disk Space:** `{format_bytes(disk.free)} free / {format_bytes(disk.total)}`\n"
            f"• **MTProto Upload Limit:** `2,000 MB (2 GB)`\n"
        )
        await event.reply(status_text)

    async def handle_doctor(event: Message):
        status_msg = await event.reply("🩺 Running `lucida doctor --live` diagnostics...")
        report = await lucida_runner.run_doctor(live=True)
        await status_msg.edit(f"🩺 **Lucida Doctor Report:**\n\n```{report}```")

    async def handle_upload_cmd(event: Message, uploader: TelethonUploader):
        """Directly upload a file from Google Cloud Shell storage up to 2GB."""
        parts = event.raw_text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.reply(f"Usage: `{config.COMMAND_PREFIX}upload <path/to/file_on_cloud_shell>`")
            return

        target_path = Path(parts[1].strip()).expanduser()
        if not target_path.exists() or not target_path.is_file():
            await event.reply(f"❌ File does not exist on disk: `{target_path}`")
            return

        file_size = target_path.stat().st_size
        status_msg = await event.reply(
            f"🚀 **Starting MTProto Direct Upload (2GB Limit)**\n"
            f"📁 `{target_path.name}` ({format_bytes(file_size)})\n"
            f"⏳ Uploading over MTProto stream..."
        )

        async def edit_chat_status(text: str):
            try:
                await status_msg.edit(text)
            except Exception:
                pass

        try:
            await uploader.upload_file(
                entity=event.chat_id,
                file_path=target_path,
                as_audio=target_path.suffix.lower() in {".flac", ".mp3", ".m4a", ".wav", ".opus", ".ogg"},
                chat_status_callback=edit_chat_status,
                show_terminal_progress=True
            )
            await status_msg.edit(
                f"✅ **Upload Complete!**\n"
                f"📁 `{target_path.name}` ({format_bytes(file_size)})\n"
                f"⚡ Sent directly via Telethon MTProto."
            )
        except Exception as e:
            await status_msg.edit(f"❌ Upload failed: `{e}`")

    async def handle_download_cmd(event: Message, uploader: TelethonUploader):
        parts = event.raw_text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.reply(f"Usage: `{config.COMMAND_PREFIX}flac <song name or link>`")
            return

        target = parts[1].strip()
        command_type, clean_target = MusicResourceParser.detect_type(target)
        await _execute_download_and_upload(event, command_type, clean_target, uploader)

    async def handle_direct_url(event: Message, url: str, uploader: TelethonUploader):
        command_type, clean_target = MusicResourceParser.detect_type(url)
        await _execute_download_and_upload(event, command_type, clean_target, uploader)

    async def _execute_download_and_upload(
        event: Message,
        command_type: str,
        target: str,
        uploader: TelethonUploader
    ):
        import uuid
        job_id = uuid.uuid4().hex[:6]
        job_dir = config.TEMP_DOWNLOAD_DIR / f"job_{job_id}"
        job_dir.mkdir(parents=True, exist_ok=True)

        status_msg = await event.reply(
            f"⚡ **FlacDL Userbot:** Fetching {command_type.capitalize()}...\n"
            f"🎯 `{target}`\n"
            f"🎵 Format: `{config.DEFAULT_FORMAT.upper()}`\n"
            f"⏳ Initializing LucidaDL..."
        )

        async def on_download_progress(status_text: str):
            try:
                await status_msg.edit(
                    f"⚡ **FlacDL Userbot:**\n"
                    f"🎯 `{target}`\n\n"
                    f"{status_text}"
                )
            except Exception:
                pass

        try:
            downloaded_files = await lucida_runner.run_download(
                command_type=command_type,
                target=target,
                out_dir=job_dir,
                format_type=config.DEFAULT_FORMAT,
                bitrate=config.DEFAULT_BITRATE,
                service=config.DEFAULT_SERVICE,
                progress_cb=on_download_progress
            )

            if not downloaded_files:
                await status_msg.edit("❌ No audio files downloaded. The track may not be available.")
                return

            total_size = sum(f.stat().st_size for f in downloaded_files)
            await status_msg.edit(
                f"📤 **Download Complete!** ({len(downloaded_files)} file(s), {format_bytes(total_size)})\n"
                f"🚀 Streaming directly to Telegram via MTProto (Bypassing 50MB limit)..."
            )

            async def on_upload_chat_status(up_text: str):
                try:
                    await status_msg.edit(up_text)
                except Exception:
                    pass

            sent_count = await uploader.upload_multiple(
                entity=event.chat_id,
                files=downloaded_files,
                as_audio=True,
                chat_status_callback=on_upload_chat_status
            )

            await status_msg.edit(
                f"✅ **Done!** Sent {sent_count} track(s) ({format_bytes(total_size)}) via Telethon MTProto.\n"
                f"Zero 50MB limitations applied!"
            )

        except Exception as e:
            await status_msg.edit(f"❌ Error occurred: `{e}`")
        finally:
            if config.CLEANUP_TEMP:
                safe_remove_directory(job_dir)
