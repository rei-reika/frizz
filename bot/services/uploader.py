import asyncio
import os
from pathlib import Path
from typing import List, Optional, Callable, Awaitable
from aiogram import Bot
from aiogram.types import FSInputFile
from bot.config import config
from bot.services.audio_metadata import AudioMetadataExtractor, AudioMetadata
from bot.utils.helpers import format_bytes, format_duration, escape_html


class TelegramUploader:
    MAX_STANDARD_SIZE = 50 * 1024 * 1024  # 50 MB limit for standard Telegram Cloud Bot API
    MAX_LOCAL_SIZE = 2000 * 1024 * 1024   # 2 GB limit for Local Bot API Server

    def __init__(self, bot: Bot):
        self.bot = bot

    async def upload_files(
        self,
        chat_id: int,
        files: List[Path],
        send_as: str = "audio",
        progress_cb: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> int:
        """
        Uploads audio files to Telegram chat.
        Returns count of successfully sent files.
        """
        if not files:
            return 0

        total_files = len(files)
        sent_count = 0
        is_local_api = bool(config.LOCAL_BOT_API_URL)
        max_allowed_size = self.MAX_LOCAL_SIZE if is_local_api else self.MAX_STANDARD_SIZE

        # Sort files naturally by name (e.g. 01 - Song, 02 - Song)
        files = sorted(files, key=lambda f: f.name)

        for index, file_path in enumerate(files, start=1):
            if not file_path.exists():
                continue

            file_size = file_path.stat().st_size
            curr_file = file_path
            temp_files_to_clean: List[Path] = []
            compressed_note = ""

            # Check file size limit
            if file_size > max_allowed_size:
                if not is_local_api and config.AUTO_COMPRESS_LARGE_FILES:
                    if progress_cb:
                        await progress_cb(
                            f"🔄 File size {format_bytes(file_size)} exceeds Telegram's 50MB limit. "
                            f"Compressing to 320kbps MP3..."
                        )

                    compressed = AudioMetadataExtractor.compress_to_mp3(file_path, "320k")
                    if compressed and compressed.exists():
                        compressed_size = compressed.stat().st_size
                        if compressed_size <= max_allowed_size:
                            curr_file = compressed
                            temp_files_to_clean.append(compressed)
                            compressed_note = (
                                f"\n<i>ℹ️ Auto-compressed from {format_bytes(file_size)} "
                                f"to {format_bytes(compressed_size)} to fit Telegram's 50MB limit.</i>"
                            )
                        else:
                            # Still too large
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
                                f"Consider setting your preference to MP3 or OPUS in /settings."
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

            # Extract rich metadata
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

            try:
                if send_as == "document":
                    doc = FSInputFile(str(curr_file))
                    thumb = FSInputFile(str(meta.thumbnail_path)) if meta.thumbnail_path and meta.thumbnail_path.exists() else None
                    await self.bot.send_document(
                        chat_id=chat_id,
                        document=doc,
                        thumbnail=thumb,
                        caption=caption,
                        parse_mode="HTML"
                    )
                else:
                    audio = FSInputFile(str(curr_file))
                    thumb = FSInputFile(str(meta.thumbnail_path)) if meta.thumbnail_path and meta.thumbnail_path.exists() else None
                    await self.bot.send_audio(
                        chat_id=chat_id,
                        audio=audio,
                        duration=meta.duration,
                        performer=meta.performer,
                        title=meta.title,
                        thumbnail=thumb,
                        caption=caption,
                        parse_mode="HTML"
                    )

                sent_count += 1
                # Small pause to avoid hitting Telegram flood limits
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
