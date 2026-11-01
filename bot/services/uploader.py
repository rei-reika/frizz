import asyncio
import time
from pathlib import Path
<<<<<<< HEAD
<<<<<<< HEAD
from typing import Optional, Callable, Any, Union, List

from telethon import TelegramClient
from telethon.tl.types import (
    DocumentAttributeAudio,
    DocumentAttributeFilename,
    TypeInputPeer
)
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn
)
from rich.console import Console

=======
=======
>>>>>>> parent of 30d016f (nice)
from typing import List, Optional, Callable, Awaitable
from aiogram import Bot
from aiogram.types import FSInputFile
from bot.config import config
<<<<<<< HEAD
>>>>>>> parent of 30d016f (nice)
=======
>>>>>>> parent of 30d016f (nice)
from bot.services.audio_metadata import AudioMetadataExtractor, AudioMetadata
from bot.utils.helpers import format_bytes, format_duration


console = Console()


<<<<<<< HEAD
<<<<<<< HEAD
def create_rich_progress() -> Progress:
    """Create a styled rich progress bar for terminal display."""
    return Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=32, complete_style="green", finished_style="bold green"),
        TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
        TextColumn("•"),
        DownloadColumn(),
        TextColumn("•"),
        TransferSpeedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
        transient=False
    )


class TelethonUploader:
    """
    Handles uploading files up to 2GB via Telethon MTProto client.send_file()
    with real-time interactive rich terminal progress and Telegram in-chat status editing.
    """

    def __init__(self, client: TelegramClient):
        self.client = client

    async def upload_file(
        self,
        entity: Union[int, str, TypeInputPeer],
        file_path: Union[str, Path],
        caption: Optional[str] = None,
        as_audio: bool = True,
        progress_callback: Optional[Callable[[int, int], Any]] = None,
        chat_status_callback: Optional[Callable[[str], Any]] = None,
        show_terminal_progress: bool = True
    ) -> Any:
        """
        Uploads a large file directly to Telegram using MTProto client.send_file().
        Bypasses standard 50MB Bot API limit (supports files up to 2GB).
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        filename = file_path.name

        # Extract audio metadata
        meta: AudioMetadata = AudioMetadataExtractor.extract(file_path)
        thumb_path = meta.thumbnail_path if (meta.thumbnail_path and meta.thumbnail_path.exists()) else None

        # Prepare Telethon document attributes
        attributes = []
        if as_audio and file_path.suffix.lower() in {".flac", ".mp3", ".m4a", ".aac", ".opus", ".ogg", ".wav"}:
            attributes.append(
                DocumentAttributeAudio(
                    duration=meta.duration or 0,
                    title=meta.title or filename,
                    performer=meta.performer or "Unknown Artist",
                    voice=False
                )
            )
        attributes.append(DocumentAttributeFilename(file_name=filename))

        # Default caption if not provided
        if not caption:
            caption = (
                f"🎵 **{meta.title or filename}**\n"
                f"👤 {meta.performer or 'Unknown Artist'}\n"
                f"💿 {meta.album or 'FlacDL'}\n"
                f"📦 {format_bytes(file_size)} *(MTProto Direct Upload)*"
            )

        # Setup Rich terminal progress bar
        rich_progress = create_rich_progress() if show_terminal_progress else None
        task_id = None
        if rich_progress:
            rich_progress.start()
            task_id = rich_progress.add_task(
                f"[bold yellow]Uploading[/] [white]{filename[:25]}[/]",
                total=file_size
            )

        last_chat_edit_time = 0.0

        def telethon_progress_adapter(current: int, total: int):
            nonlocal last_chat_edit_time

            # 1. Update rich terminal bar
            if rich_progress and task_id is not None:
                rich_progress.update(task_id, completed=current, total=total)

            # 2. Invoke caller's custom progress callback if provided
            if progress_callback:
                try:
                    res = progress_callback(current, total)
                    if asyncio.iscoroutine(res):
                        asyncio.create_task(res)
                except Exception:
                    pass

            # 3. Debounced in-chat Telegram status updater (every 2.5 seconds)
            now = time.time()
            if chat_status_callback and (now - last_chat_edit_time > 2.5 or current >= total):
                last_chat_edit_time = now
                pct = (current / total * 100) if total > 0 else 0
                status_text = (
                    f"📤 **Uploading to Telegram (MTProto 2GB)**\n"
                    f"📁 `{filename}`\n"
                    f"📊 `{current / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB` ({pct:.1f}%)\n"
=======
=======
>>>>>>> parent of 30d016f (nice)
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
>>>>>>> parent of 30d016f (nice)
                )
                try:
                    res = chat_status_callback(status_text)
                    if asyncio.iscoroutine(res):
                        asyncio.create_task(res)
                except Exception:
                    pass

        try:
            sent_message = await self.client.send_file(
                entity=entity,
                file=file_path,
                caption=caption,
                thumb=thumb_path,
                attributes=attributes,
                progress_callback=telethon_progress_adapter,
                force_document=not as_audio
            )
            return sent_message

<<<<<<< HEAD
<<<<<<< HEAD
        finally:
            if rich_progress:
                rich_progress.stop()
            # Clean up extracted temp thumbnail image
            if thumb_path and thumb_path.exists() and thumb_path.suffix == ".jpg" and ".thumb." in thumb_path.name:
                try:
                    thumb_path.unlink(missing_ok=True)
                except Exception:
                    pass

    async def upload_multiple(
        self,
        entity: Union[int, str, TypeInputPeer],
        files: List[Path],
        as_audio: bool = True,
        chat_status_callback: Optional[Callable[[str], Any]] = None
    ) -> int:
        """Upload multiple files sequentially with progress reporting."""
        total = len(files)
        sent = 0
        sorted_files = sorted(files, key=lambda f: f.name)

        for index, f in enumerate(sorted_files, 1):
            if chat_status_callback:
                await chat_status_callback(f"📤 Preparing file ({index}/{total}): **{f.name}**...")
            try:
                await self.upload_file(
                    entity=entity,
                    file_path=f,
                    as_audio=as_audio,
                    chat_status_callback=chat_status_callback
                )
                sent += 1
                if index < total:
                    await asyncio.sleep(1.0)
=======
=======
>>>>>>> parent of 30d016f (nice)
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

>>>>>>> parent of 30d016f (nice)
            except Exception as e:
                console.print(f"[bold red]Failed to upload {f.name}: {e}[/]")

        return sent
