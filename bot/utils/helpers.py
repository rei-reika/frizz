import html
import shutil
from pathlib import Path
from typing import Union


def format_bytes(size: Union[int, float]) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size) < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def format_duration(seconds: Union[int, float]) -> str:
    """Format seconds into MM:SS or HH:MM:SS."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def escape_html(text: str) -> str:
    """Escape text for Telegram HTML parse mode."""
    if not text:
        return ""
    return html.escape(str(text))


def generate_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Generate visual progress bar string."""
    if total <= 0:
        return "░" * length
    fraction = min(max(current / total, 0.0), 1.0)
    filled_len = int(round(length * fraction))
    return "█" * filled_len + "░" * (length - filled_len)


def safe_remove_directory(path: Union[str, Path]):
    """Safely delete directory tree without raising errors."""
    try:
        p = Path(path)
        if p.exists() and p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass
