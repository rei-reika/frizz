import re
from typing import Tuple
from urllib.parse import urlparse, parse_qs


class MusicResourceParser:
    URL_REGEX = re.compile(
        r'^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/.*)?$',
        re.IGNORECASE
    )

    @classmethod
    def is_url(cls, text: str) -> bool:
        """Check if input string is an HTTP/HTTPS URL."""
        text = text.strip()
        return bool(cls.URL_REGEX.match(text))

    @classmethod
    def detect_type(cls, input_str: str) -> Tuple[str, str]:
        """
        Detects whether input is a track, album, playlist, or general search.
        Returns (command_type, cleaned_target)
        command_type: 'track', 'album', 'playlist'
        """
        input_str = input_str.strip()
        if not cls.is_url(input_str):
            # Not a URL: Default text search to 'track'
            return "track", input_str

        url = input_str
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()
        query = parse_qs(parsed.query)

        # 1. Spotify
        if "spotify.com" in netloc:
            if "/album/" in path:
                return "album", url
            elif "/playlist/" in path:
                return "playlist", url
            elif "/track/" in path:
                return "track", url

        # 2. Apple Music
        if "apple.com" in netloc:
            if "/playlist/" in path:
                return "playlist", url
            elif "/album/" in path:
                # Apple Music tracks in albums often have ?i=123456
                if "i" in query:
                    return "track", url
                return "album", url

        # 3. Deezer
        if "deezer.com" in netloc:
            if "/album/" in path:
                return "album", url
            elif "/playlist/" in path:
                return "playlist", url
            elif "/track/" in path:
                return "track", url

        # 4. Tidal
        if "tidal.com" in netloc:
            if "/album/" in path:
                return "album", url
            elif "/playlist/" in path:
                return "playlist", url
            elif "/track/" in path:
                return "track", url

        # 5. Qobuz
        if "qobuz.com" in netloc:
            if "/album/" in path:
                return "album", url
            elif "/track/" in path:
                return "track", url
            elif "/playlist/" in path:
                return "playlist", url

        # 6. SoundCloud
        if "soundcloud.com" in netloc:
            if "/sets/" in path:
                return "playlist", url
            return "track", url

        # 7. Amazon Music
        if "amazon." in netloc:
            if "/playlists/" in path:
                return "playlist", url
            elif "/albums/" in path:
                return "album", url
            elif "/tracks/" in path:
                return "track", url

        # 8. YouTube / YouTube Music
        if "youtube.com" in netloc or "youtu.be" in netloc:
            if "list" in query:
                return "playlist", url
            return "track", url

        # Generic URL fallback: default to track
        return "track", url
