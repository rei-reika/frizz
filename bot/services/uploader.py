import asyncio
import os
from pathlib import Path
from typing import List, Optional, Callable, Awaitable, Dict, Any
from aiogram import Bot
from aiogram.types import FSInputFile, Message
from bot.config import config
from bot.database import db
from bot.services.audio_metadata import AudioMetadataExtractor, AudioMetadata
from bot.utils.helpers import format_bytes, format_duration, escape_html


class TelegramUploader:
    MAX_STANDARD_SIZE = 50 * 1024 * 1024  # 50 MB limit for standard Telegram Cloud Bot API
    MAX_LOCAL_SIZE = 2000 * 1024 * 1024   # 2 GB limit for Local Bot API Server

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_cached_file(
        self,
        chat_id: int,
        cached: Dict[str, Any],
        custom_caption: Optional[str] = None
    ) -> bool:
        """
        Send a file instantly using Telegram's file_id.
        Bypasses local re-upload and bypasses the 50MB upload limit!
        """
        title = cached.get("title") or cached.get("file_name", "Audio Track")
        performer = cached.get("performer") or "Unknown Artist"
        file_size = cached.get("file_size", 0)

        caption = custom_caption or (
            f"🎵 <b>{escape_html(title)}</b>\n"
            f"👤 {escape_html(performer)}\n"
            f"📦 {format_bytes(file_size)} <i>(Instant Cloud Cache ⚡)</i>"
        )

        media_type = cached.get("media_type", "audio")
        file_id = cached["file_id"]

        if media_type == "document":
            await self.bot.send_document(
                chat_id=chat_id,
                document=file_id,
                caption=caption,
                parse_mode="HTML"
            )
        else:
            await self.bot.send_audio(
                chat_id=chat_id,
                audio=file_id,
                duration=cached.get("duration", 0),
                performer=performer,
                title=title,
                caption=caption,
                parse_mode="HTML"
            )
        return True

    async def upload_files(
        self,
        chat_id: int,
        files: List[Path],
        send_as: str = "audio",
        progress_cb: Optional[Callable[[str], Awaitable[None]]] = None,
        query_target: Optional[str] = None,
        format_type: str = "flac"
    ) -> int:
        """
        Uploads audio files to Telegram chat.
        Checks cache for file_id first; if not present, uploads and caches the file_id.
        Returns count of successfully sent files.
        """
        if not files:
            return 0

        total_files = len(files)
        sent_count = 0
        is_local_api = bool(config.LOCAL_BOT_API_URL)
        max_allowed_size = self.MAX_LOCAL_SIZE if is_local_api else self.MAX_STANDARD_SIZE

        # Sort files naturally by name
        files = sorted(files, key=lambda f: f.name)

        for index, file_path in enumerate(files, start=1):
            if not file_path.exists():
                continue

            file_size = file_path.stat().st_size
            curr_file = file_path
            temp_files_to_clean: List[Path] = []
            compressed_note = ""

            # 1. CHECK CACHE FIRST: Check if this file was already uploaded to Telegram
            file_key = file_path.name.lower().strip()
            cached = await db.get_cached_file(file_key)

            if cached and cached.get("file_id"):
                if progress_cb:
                    await progress_cb(
                        f"⚡ Sending ({index}/{total_files}) from Telegram Cloud Cache: "
                        f"<b>{escape_html(cached.get('title') or file_path.name)}</b>..."
                    )

                caption = (
                    f"🎵 <b>{escape_html(cached.get('title') or file_path.name)}</b>\n"
                    f"👤 {escape_html(cached.get('performer') or 'Unknown Artist')}\n"
                    f"📦 {format_bytes(cached.get('file_size', file_size))} <i>(Cloud Cache ⚡)</i>"
                )

                try:
                    await self.send_cached_file(chat_id, cached, custom_caption=caption)
                    sent_count += 1
                    if total_files > 1 and index < total_files:
                        await asyncio.sleep(0.5)
                    continue
                except Exception:
                    # If sending by file_id fails (e.g. file was deleted or invalid), fallback to uploading
                    pass

            # 2. CHECK FILE SIZE LIMIT (For initial first-time upload)
            if file_size > max_allowed_size:
                if not is_local_api and config.AUTO_COMPRESS_LARGE_FILES:
                    if progress_cb:
                        await progress_cb(
                            f"🔄 File size {format_bytes(file_size)} exceeds Telegram's 50MB limit. "
                            f"Compressing to 320kbps MP3 for initial cache..."
                        )

                    compressed = AudioMetadataExtractor.compress_to_mp3(file_path, "320k")
                    if compressed and compressed.exists():
                        compressed_size = compressed.stat().st_size
                        if compressed_size <= max_allowed_size:
                            curr_file = compressed
                            temp_files_to_clean.append(compressed)
                            compressed_note = (
                                f"\n<i>ℹ️ Compressed from {format_bytes(file_size)} "
                                f"to {format_bytes(compressed_size)} for initial Telegram upload.</i>"
                            )
                        else:
                            temp_files_to_clean.append(compressed)
                            await self.bot.send_message(
                                chat_id=chat_id,
                                text=(
                                    f"⚠️ <b>Skipped file:</b> {escape_html(file_path.name)}\n"
                                    f"Size: {format_bytes(file_size)} (even compressed: {format_bytes(compressed_size)}).\n"
                                    f"Exceeds standard Telegram Bot API 50MB upload limit."
                                ),
                                parse_mode="HTML"
                            )
                            continue
                    else:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=(
                                f"⚠️ <b>Skipped file:</b> {escape_html(file_path.name)}\n"
                                f"Size: {format_bytes(file_size)} (> 50MB limit).\n"
                                f"Consider setting your preference to MP3 or OPUS in /settings, "
                                f"or ask an admin to pre-cache this file via Telegram."
                            ),
                            parse_mode="HTML"
                        )
                        continue
                else:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"⚠️ <b>Skipped file:</b> {escape_html(file_path.name)}\n"
                            f"Size: {format_bytes(file_size)} (> 50MB limit)."
                        ),
                        parse_mode="HTML"
                    )
                    continue

            # 3. EXTRACT METADATA
            meta: AudioMetadata = AudioMetadataExtractor.extract(curr_file)
            if meta.thumbnail_path and meta.thumbnail_path.exists():
                temp_files_to_clean.append(meta.thumbnail_path)

            if progress_cb:
                await progress_cb(
                    f"📤 Uploading ({index}/{total_files}): <b>{escape_html(meta.title)}</b>..."
                )

            caption = (
                f"🎵 <b>{escape_html(meta.title)}</b>\n"
                f"👤 {escape_html(meta.performer)}\n"
                f"💿 {escape_html(meta.album)}\n"
                f"📦 {format_bytes(curr_file.stat().st_size)}"
                f"{compressed_note}"
            )

            # 4. FIRST-TIME UPLOAD & CAPTURE file_id
            try:
                sent_msg: Message
                if send_as == "document":
                    doc = FSInputFile(str(curr_file))
                    thumb = FSInputFile(str(meta.thumbnail_path)) if meta.thumbnail_path and meta.thumbnail_path.exists() else None
                    sent_msg = await self.bot.send_document(
                        chat_id=chat_id,
                        document=doc,
                        thumbnail=thumb,
                        caption=caption,
                        parse_mode="HTML"
                    )
                    captured_file_id = sent_msg.document.file_id
                    captured_unique_id = sent_msg.document.file_unique_id
                else:
                    audio = FSInputFile(str(curr_file))
                    thumb = FSInputFile(str(meta.thumbnail_path)) if meta.thumbnail_path and meta.thumbnail_path.exists() else None
                    sent_msg = await self.bot.send_audio(
                        chat_id=chat_id,
                        audio=audio,
                        duration=meta.duration,
                        performer=meta.performer,
                        title=meta.title,
                        thumbnail=thumb,
                        caption=caption,
                        parse_mode="HTML"
                    )
                    captured_file_id = sent_msg.audio.file_id
                    captured_unique_id = sent_msg.audio.file_unique_id

                # 5. STORE file_id IN DATABASE CACHE FOR FUTURE REQUESTS
                await db.save_cached_file(
                    file_key=file_key,
                    file_id=captured_file_id,
                    file_unique_id=captured_unique_id,
                    file_name=file_path.name,
                    file_size=file_size,
                    media_type=send_as,
                    title=meta.title,
                    performer=meta.performer,
                    duration=meta.duration
                )

                # Also save artist-title alias key if available
                if meta.performer and meta.title:
                    alias_key = f"{meta.performer} - {meta.title}.{file_path.suffix.lstrip('.')}".lower()
                    if alias_key != file_key:
                        await db.save_cached_file(
                            file_key=alias_key,
                            file_id=captured_file_id,
                            file_unique_id=captured_unique_id,
                            file_name=file_path.name,
                            file_size=file_size,
                            media_type=send_as,
                            title=meta.title,
                            performer=meta.performer,
                            duration=meta.duration
                        )

                # If this was a single track requested via query or URL, also cache the query key!
                if query_target and total_files == 1:
                    query_key = f"query:{query_target.strip().lower()}:{format_type.lower()}"
                    await db.save_cached_file(
                        file_key=query_key,
                        file_id=captured_file_id,
                        file_unique_id=captured_unique_id,
                        file_name=file_path.name,
                        file_size=file_size,
                        media_type=send_as,
                        title=meta.title,
                        performer=meta.performer,
                        duration=meta.duration
                    )

                sent_count += 1
                if total_files > 1 and index < total_files:
                    await asyncio.sleep(0.8)

            except Exception as e:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Failed to upload {escape_html(curr_file.name)}: {escape_html(str(e))}",
                    parse_mode="HTML"
                )
            finally:
                for tf in temp_files_to_clean:
                    try:
                        if tf.exists():
                            tf.unlink(missing_ok=True)
                    except Exception:
                        pass

        return sent_count
