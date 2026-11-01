import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telethon MTProto Authentication (from https://my.telegram.org)
    API_ID: int = Field(default=0, description="Telegram App API ID")
    API_HASH: str = Field(default="", description="Telegram App API HASH")
    PHONE_NUMBER: Optional[str] = Field(default=None, description="Optional phone number for initial login")

    # CRITICAL: Persistent Session storage in Google Cloud Shell ($HOME)
    # Cloud Shell only persists files under /home/<user>. Everything else is ephemeral!
    SESSION_NAME: str = Field(default="flacdl_userbot")
    SESSION_DIR: Path = Field(default=Path.home() / ".telethon_sessions")

    # Command configuration
    COMMAND_PREFIX: str = Field(default=".", description="Prefix for userbot commands (e.g. .flac, .upload)")
    
    # Allowed users who can trigger the userbot (leave empty for owner-only)
    ALLOWED_USERS_RAW: str = Field(default="", alias="ALLOWED_USERS")

    # LucidaDL binary configuration
    LUCIDA_BIN: str = Field(default="auto")
    DEFAULT_FORMAT: str = Field(default="flac")
    DEFAULT_BITRATE: str = Field(default="320k")
    DEFAULT_SERVICE: str = Field(default="default")

    # Storage paths
    # Note: store downloads inside $HOME to avoid losing incomplete tasks on Cloud Shell
    TEMP_DOWNLOAD_DIR: Path = Field(default=Path.home() / "t-server" / "downloads")
    CLEANUP_TEMP: bool = Field(default=True)
    DOWNLOAD_TIMEOUT_SECONDS: int = Field(default=900)

    # SQLite database file (stored in persistent storage)
    DB_PATH: Path = Field(default=Path(__file__).resolve().parent.parent / "flacdl_data.sqlite3")

    @property
    def session_file_path(self) -> Path:
        """
        Returns the absolute session file path without extension
        (Telethon automatically appends '.session').
        Guarantees creation inside persistent $HOME on Google Cloud Shell.
        """
        try:
            self.SESSION_DIR.mkdir(parents=True, exist_ok=True)
            # Test write access
            test_file = self.SESSION_DIR / ".write_test"
            test_file.touch()
            test_file.unlink(missing_ok=True)
            return self.SESSION_DIR / self.SESSION_NAME
        except (OSError, PermissionError):
            # Fallback to project root .sessions/ (also inside $HOME on Cloud Shell)
            fallback = Path(__file__).resolve().parent.parent / ".sessions"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback / self.SESSION_NAME

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

    def is_user_allowed(self, user_id: int, my_id: Optional[int] = None) -> bool:
        """Owner is always allowed. Others are allowed if in whitelist."""
        if my_id and user_id == my_id:
            return True
        allowed = self.allowed_users
        if not allowed:
            # If no whitelist specified, only owner can execute
            return user_id == my_id
        return user_id in allowed


config = Settings()
