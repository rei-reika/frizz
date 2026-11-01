import datetime
from pathlib import Path
from typing import Dict, Any, Optional
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

            return {
                "total_users": total_users,
                "total_downloads": total_downloads,
                "successful_downloads": successful_downloads,
                "total_files_sent": total_files
            }

    async def get_all_user_ids(self) -> list[int]:
        """Fetch all user IDs for broadcasting."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id FROM user_settings") as cur:
                rows = await cur.fetchall()
                return [row[0] for row in rows]


db = Database(config.DB_PATH)
