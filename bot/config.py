import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BOT_TOKEN: str = Field(default="", description="Telegram Bot API Token")

    ALLOWED_USERS_RAW: str = Field(default="", alias="ALLOWED_USERS")
    ADMIN_IDS_RAW: str = Field(default="", alias="ADMIN_IDS")

    LUCIDA_BIN: str = Field(default="auto")
    MAX_CONCURRENT_DOWNLOADS: int = Field(default=2)
    DOWNLOAD_TIMEOUT_SECONDS: int = Field(default=600)

    DEFAULT_FORMAT: str = Field(default="flac")
    DEFAULT_BITRATE: str = Field(default="320k")
    DEFAULT_SERVICE: str = Field(default="default")

    TEMP_DOWNLOAD_DIR: Path = Field(default=Path("/tmp/flacdl_bot"))
    CLEANUP_TEMP: bool = Field(default=True)
    AUTO_COMPRESS_LARGE_FILES: bool = Field(default=True)

    LOCAL_BOT_API_URL: Optional[str] = Field(default=None)
    DB_PATH: Path = Field(default=Path("bot_data.sqlite3"))

    # Parsed user lists
    @property
    def allowed_users(self) -> List[int]:
        if not self.ALLOWED_USERS_RAW or not self.ALLOWED_USERS_RAW.strip():
            return []
        ids = []
        for x in self.ALLOWED_USERS_RAW.split(","):
            x = x.strip()
            if x.isdigit():
                ids.append(int(x))
        return ids

    @property
    def admin_ids(self) -> List[int]:
        if not self.ADMIN_IDS_RAW or not self.ADMIN_IDS_RAW.strip():
            return []
        ids = []
        for x in self.ADMIN_IDS_RAW.split(","):
            x = x.strip()
            if x.isdigit():
                ids.append(int(x))
        return ids

    def is_user_allowed(self, user_id: int) -> bool:
        """Return True if user is allowed to use the bot."""
        allowed = self.allowed_users
        if not allowed:
            return True  # Public mode
        return user_id in allowed or self.is_admin(user_id)

    def is_admin(self, user_id: int) -> bool:
        """Return True if user is an admin."""
        return user_id in self.admin_ids


# Global config instance
config = Settings()
