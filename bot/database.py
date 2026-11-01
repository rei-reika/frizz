import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import aiosqlite
from bot.config import config


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def init(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    audio_format TEXT DEFAULT 'flac',
                    bitrate TEXT DEFAULT '320k',
                    service TEXT DEFAULT 'default',
                    send_as TEXT DEFAULT 'audio',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS download_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    query TEXT,
                    command_type TEXT,
                    status TEXT,
                    files_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_key TEXT UNIQUE NOT NULL,
                    file_id TEXT NOT NULL,
                    file_unique_id TEXT,
                    file_name TEXT,
                    file_size INTEGER DEFAULT 0,
                    media_type TEXT DEFAULT 'audio',
                    title TEXT,
                    performer TEXT,
                    duration INTEGER DEFAULT 0,
                    access_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_file_cache_key ON file_cache (file_key);")
            await db.commit()

    async def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Fetch user settings, inserting defaults if not present."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT audio_format, bitrate, service, send_as FROM user_settings WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)

            # Insert defaults
            default_settings = {
                "audio_format": config.DEFAULT_FORMAT,
                "bitrate": config.DEFAULT_BITRATE,
                "service": config.DEFAULT_SERVICE,
                "send_as": "audio"
            }
            await db.execute(
                """
                INSERT OR IGNORE INTO user_settings (user_id, audio_format, bitrate, service, send_as)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    default_settings["audio_format"],
                    default_settings["bitrate"],
                    default_settings["service"],
                    default_settings["send_as"]
                )
            )
            await db.commit()
            return default_settings

    async def update_user_setting(self, user_id: int, key: str, value: Any):
        """Update a specific setting for a user."""
        allowed_keys = {"audio_format", "bitrate", "service", "send_as"}
        if key not in allowed_keys:
            raise ValueError(f"Invalid setting key: {key}")

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""
                INSERT INTO user_settings (user_id, {key}, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    {key} = excluded.{key},
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (user_id, value)
            )
            await db.commit()

    async def log_download(
        self,
        user_id: int,
        query: str,
        command_type: str,
        status: str,
        files_count: int = 0,
        error_message: Optional[str] = None
    ):
        """Record download task in history."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO download_history (user_id, query, command_type, status, files_count, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, query, command_type, status, files_count, error_message)
            )
            await db.commit()

    # =========================================================================
    # Telegram file_id Caching System
    # =========================================================================

    @staticmethod
    def normalize_key(key: str) -> str:
        """Normalize key for case-insensitive matching."""
        if not key:
            return ""
        return key.strip().lower()

    async def get_cached_file(self, file_key: str) -> Optional[Dict[str, Any]]:
        """
        Look up a cached Telegram file by its key (filename, query, or track hash).
        If found, updates access_count and last_accessed timestamp.
        """
        norm_key = self.normalize_key(file_key)
        if not norm_key:
            return None

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, file_key, file_id, file_unique_id, file_name,
                       file_size, media_type, title, performer, duration, access_count
                FROM file_cache
                WHERE file_key = ?
                """,
                (norm_key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    # Update stats
                    await db.execute(
                        """
                        UPDATE file_cache
                        SET access_count = access_count + 1,
                            last_accessed = CURRENT_TIMESTAMP
                        WHERE file_key = ?
                        """,
                        (norm_key,)
                    )
                    await db.commit()
                    return dict(row)
        return None

    async def save_cached_file(
        self,
        file_key: str,
        file_id: str,
        file_unique_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: int = 0,
        media_type: str = "audio",
        title: Optional[str] = None,
        performer: Optional[str] = None,
        duration: int = 0
    ) -> bool:
        """
        Save or update a Telegram file_id mapping in the database.
        """
        norm_key = self.normalize_key(file_key)
        if not norm_key or not file_id:
            return False

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO file_cache (
                    file_key, file_id, file_unique_id, file_name,
                    file_size, media_type, title, performer, duration,
                    access_count, last_accessed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(file_key) DO UPDATE SET
                    file_id = excluded.file_id,
                    file_unique_id = excluded.file_unique_id,
                    file_name = COALESCE(excluded.file_name, file_cache.file_name),
                    file_size = excluded.file_size,
                    media_type = excluded.media_type,
                    title = COALESCE(excluded.title, file_cache.title),
                    performer = COALESCE(excluded.performer, file_cache.performer),
                    duration = excluded.duration,
                    last_accessed = CURRENT_TIMESTAMP;
                """,
                (
                    norm_key,
                    file_id,
                    file_unique_id,
                    file_name,
                    file_size,
                    media_type,
                    title,
                    performer,
                    duration
                )
            )
            await db.commit()
            return True

    async def delete_cached_file(self, file_key: str) -> bool:
        """Remove a cached file entry by key."""
        norm_key = self.normalize_key(file_key)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM file_cache WHERE file_key = ?", (norm_key,))
            await db.commit()
            return cursor.rowcount > 0

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Fetch statistics about cached files."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM file_cache") as cur:
                total_files = (await cur.fetchone())[0]

            async with db.execute("SELECT COALESCE(SUM(file_size), 0) FROM file_cache") as cur:
                total_size = (await cur.fetchone())[0]

            async with db.execute("SELECT COALESCE(SUM(access_count), 0) FROM file_cache") as cur:
                total_hits = (await cur.fetchone())[0]

            async with db.execute(
                "SELECT COALESCE(SUM(file_size * (access_count - 1)), 0) FROM file_cache WHERE access_count > 1"
            ) as cur:
                saved_bandwidth = (await cur.fetchone())[0]

            return {
                "total_cached_files": total_files,
                "total_cached_size": total_size,
                "total_cache_hits": total_hits,
                "saved_bandwidth": saved_bandwidth
            }

    async def list_cached_files(self, limit: int = 15) -> List[Dict[str, Any]]:
        """List recently accessed cached files."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT file_key, file_name, file_size, media_type, title, performer, access_count, last_accessed
                FROM file_cache
                ORDER BY last_accessed DESC
                LIMIT ?
                """,
                (limit,)
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    # =========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Fetch general bot statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM user_settings") as cur:
                total_users = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM download_history") as cur:
                total_downloads = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM download_history WHERE status = 'completed'") as cur:
                successful_downloads = (await cur.fetchone())[0]

            async with db.execute("SELECT COALESCE(SUM(files_count), 0) FROM download_history WHERE status = 'completed'") as cur:
                total_files = (await cur.fetchone())[0]

            cache_stats = await self.get_cache_stats()

            return {
                "total_users": total_users,
                "total_downloads": total_downloads,
                "successful_downloads": successful_downloads,
                "total_files_sent": total_files,
                "cached_files": cache_stats["total_cached_files"],
                "cache_hits": cache_stats["total_cache_hits"]
            }

    async def get_all_user_ids(self) -> list[int]:
        """Fetch all user IDs for broadcasting."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id FROM user_settings") as cur:
                rows = await cur.fetchall()
                return [row[0] for row in rows]


db = Database(config.DB_PATH)
