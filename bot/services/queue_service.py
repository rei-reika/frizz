import asyncio
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from bot.config import config
from bot.database import db
from bot.keyboards import get_cancel_keyboard
from bot.services.lucida import lucida_runner
from bot.services.uploader import TelegramUploader
from bot.utils.helpers import escape_html, safe_remove_directory


@dataclass
class DownloadJob:
    job_id: str
    user_id: int
    chat_id: int
    command_type: str  # 'track', 'album', 'playlist'
    target: str        # url or query string
    settings: Dict[str, Any]
    status_message_id: int
    created_at: float = field(default_factory=time.time)
    status: str = "queued"  # 'queued', 'downloading', 'uploading', 'completed', 'failed', 'cancelled'
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    task: Optional[asyncio.Task] = None


class QueueManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.uploader = TelegramUploader(bot)
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)
        self.jobs: Dict[str, DownloadJob] = {}
        self.waiting_queue: asyncio.Queue[DownloadJob] = asyncio.Queue()
        self._last_edit_time: Dict[int, float] = {}
        self._is_running = False
        self._worker_tasks: list[asyncio.Task] = []

    def start(self):
        """Start worker tasks for processing jobs."""
        if self._is_running:
            return
        self._is_running = True
        for i in range(config.MAX_CONCURRENT_DOWNLOADS):
            t = asyncio.create_task(self._worker_loop(i))
            self._worker_tasks.append(t)

    async def stop(self):
        """Gracefully stop queue workers and cancel jobs."""
        self._is_running = False
        for job in list(self.jobs.values()):
            job.cancel_event.set()
        for t in self._worker_tasks:
            t.cancel()

    async def submit_job(
        self,
        user_id: int,
        chat_id: int,
        command_type: str,
        target: str,
        settings: Dict[str, Any],
        status_message_id: int
    ) -> DownloadJob:
        """Submit a new download job to the queue."""
        job_id = uuid.uuid4().hex[:8]
        job = DownloadJob(
            job_id=job_id,
            user_id=user_id,
            chat_id=chat_id,
            command_type=command_type,
            target=target,
            settings=settings,
            status_message_id=status_message_id
        )
        self.jobs[job_id] = job
        await self.waiting_queue.put(job)
        return job

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued or active job."""
        if job_id not in self.jobs:
            return False
        job = self.jobs[job_id]
        job.status = "cancelled"
        job.cancel_event.set()
        if job.task and not job.task.done():
            job.task.cancel()
        return True

    def get_queue_position(self, job_id: str) -> int:
        """Get position in queue for a job."""
        pos = 1
        for j in self.jobs.values():
            if j.status == "queued":
                if j.job_id == job_id:
                    return pos
                pos += 1
        return 0

    async def _safe_edit_status(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        force: bool = False
    ):
        """Edit status message with throttle protection (max once every 1.5s)."""
        now = time.time()
        last_time = self._last_edit_time.get(message_id, 0.0)
        if not force and (now - last_time < 1.5):
            return

        self._last_edit_time[message_id] = now
        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception:
            # Message not modified or transient Telegram error
            pass

    async def _worker_loop(self, worker_id: int):
        """Worker task processing queued downloads."""
        while self._is_running:
            job = await self.waiting_queue.get()
            if job.status == "cancelled":
                self.waiting_queue.task_done()
                continue

            async with self.semaphore:
                job.task = asyncio.current_task()
                await self._process_job(job)

            self.waiting_queue.task_done()

    async def _process_job(self, job: DownloadJob):
        """Execute a single job: download, transcode, upload, cleanup."""
        job_dir = config.TEMP_DOWNLOAD_DIR / f"job_{job.job_id}"
        files_sent = 0

        try:
            # 1. PRE-CHECK CACHE: Check if this target/query is already cached in Telegram cloud!
            format_type = job.settings.get("audio_format", "flac").lower()
            query_key = f"query:{job.target.strip().lower()}:{format_type}"
            cached = await db.get_cached_file(query_key)
            if not cached:
                cached = await db.get_cached_file(job.target.strip().lower())

            if cached and cached.get("file_id"):
                job.status = "uploading"
                await self._safe_edit_status(
                    chat_id=job.chat_id,
                    message_id=job.status_message_id,
                    text=(
                        f"⚡ <b>Found in Telegram Cloud Cache!</b>\n"
                        f"🎯 <code>{escape_html(job.target)}</code>\n\n"
                        f"🚀 Sending <b>{escape_html(cached.get('title') or cached.get('file_name'))}</b> "
                        f"instantly using cached Telegram file_id (bypassing download & 50MB limits)..."
                    ),
                    reply_markup=None,
                    force=True
                )
                await self.uploader.send_cached_file(
                    chat_id=job.chat_id,
                    cached=cached
                )
                job.status = "completed"
                await self._safe_edit_status(
                    chat_id=job.chat_id,
                    message_id=job.status_message_id,
                    text=f"✅ <b>Done!</b> Sent track instantly from Telegram cloud cache. Enjoy your music!",
                    reply_markup=None,
                    force=True
                )
                await db.log_download(
                    user_id=job.user_id,
                    query=job.target,
                    command_type=job.command_type,
                    status="completed",
                    files_count=1
                )
                return

            job.status = "downloading"
            cancel_kb = get_cancel_keyboard(job.job_id)

            await self._safe_edit_status(
                chat_id=job.chat_id,
                message_id=job.status_message_id,
                text=(
                    f"⚡ <b>Downloading {job.command_type.capitalize()}</b>\n"
                    f"🎯 <code>{escape_html(job.target)}</code>\n"
                    f"🎵 Format: <b>{job.settings.get('audio_format', 'flac').upper()}</b> | "
                    f"🌐 Service: <b>{job.settings.get('service', 'default').capitalize()}</b>\n\n"
                    f"⏳ Initializing download session..."
                ),
                reply_markup=cancel_kb,
                force=True
            )

            async def on_progress(status_text: str):
                await self._safe_edit_status(
                    chat_id=job.chat_id,
                    message_id=job.status_message_id,
                    text=(
                        f"⚡ <b>Downloading {job.command_type.capitalize()}</b>\n"
                        f"🎯 <code>{escape_html(job.target)}</code>\n\n"
                        f"{escape_html(status_text)}"
                    ),
                    reply_markup=cancel_kb
                )

            downloaded_files = await lucida_runner.run_download(
                command_type=job.command_type,
                target=job.target,
                out_dir=job_dir,
                format_type=job.settings.get("audio_format", "flac"),
                bitrate=job.settings.get("bitrate", "320k"),
                service=job.settings.get("service", "default"),
                progress_cb=on_progress,
                cancel_event=job.cancel_event
            )

            if not downloaded_files:
                raise RuntimeError("No audio files were downloaded. The track might not be available on this service.")

            job.status = "uploading"
            await self._safe_edit_status(
                chat_id=job.chat_id,
                message_id=job.status_message_id,
                text=f"📤 Uploading {len(downloaded_files)} file(s) to Telegram...",
                reply_markup=None,
                force=True
            )

            async def on_upload_progress(upload_text: str):
                await self._safe_edit_status(
                    chat_id=job.chat_id,
                    message_id=job.status_message_id,
                    text=upload_text,
                    reply_markup=None
                )

            files_sent = await self.uploader.upload_files(
                chat_id=job.chat_id,
                files=downloaded_files,
                send_as=job.settings.get("send_as", "audio"),
                progress_cb=on_upload_progress,
                query_target=job.target,
                format_type=job.settings.get("audio_format", "flac")
            )

            job.status = "completed"
            await self._safe_edit_status(
                chat_id=job.chat_id,
                message_id=job.status_message_id,
                text=f"✅ <b>Done!</b> Sent {files_sent} audio track(s). Enjoy your music!",
                reply_markup=None,
                force=True
            )

            await db.log_download(
                user_id=job.user_id,
                query=job.target,
                command_type=job.command_type,
                status="completed",
                files_count=files_sent
            )

        except asyncio.CancelledError:
            job.status = "cancelled"
            await self._safe_edit_status(
                chat_id=job.chat_id,
                message_id=job.status_message_id,
                text=f"❌ Download cancelled.",
                reply_markup=None,
                force=True
            )
            await db.log_download(
                user_id=job.user_id,
                query=job.target,
                command_type=job.command_type,
                status="cancelled"
            )

        except Exception as e:
            job.status = "failed"
            error_msg = str(e)
            await self._safe_edit_status(
                chat_id=job.chat_id,
                message_id=job.status_message_id,
                text=f"❌ <b>Download Failed:</b>\n{escape_html(error_msg)}",
                reply_markup=None,
                force=True
            )
            await db.log_download(
                user_id=job.user_id,
                query=job.target,
                command_type=job.command_type,
                status="failed",
                error_message=error_msg
            )

        finally:
            if config.CLEANUP_TEMP:
                safe_remove_directory(job_dir)
            if job.job_id in self.jobs:
                del self.jobs[job.job_id]


queue_manager: Optional[QueueManager] = None


def init_queue(bot: Bot) -> QueueManager:
    global queue_manager
    queue_manager = QueueManager(bot)
    queue_manager.start()
    return queue_manager
