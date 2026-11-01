import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus


@dataclass
class AudioMetadata:
    title: str
    performer: str
    album: str
    duration: int
    thumbnail_path: Optional[Path] = None


class AudioMetadataExtractor:
    @staticmethod
    def extract(file_path: Path) -> AudioMetadata:
        """
        Extract title, performer, album, duration, and embedded cover art.
        """
        file_path = Path(file_path)
        stem = file_path.stem
        default_title = stem
        default_performer = "Unknown Artist"
        default_album = "Unknown Album"
        duration = 0
        thumbnail_path: Optional[Path] = None

        try:
            audio = mutagen.File(str(file_path))
            if audio is not None:
                if hasattr(audio.info, "length"):
                    duration = int(audio.info.length)

                # 1. FLAC
                if isinstance(audio, FLAC):
                    if "title" in audio and audio["title"]:
                        default_title = audio["title"][0]
                    if "artist" in audio and audio["artist"]:
                        default_performer = audio["artist"][0]
                    if "album" in audio and audio["album"]:
                        default_album = audio["album"][0]

                    # Cover art
                    if audio.pictures:
                        pic: Picture = audio.pictures[0]
                        thumb_file = file_path.with_suffix(".thumb.jpg")
                        thumb_file.write_bytes(pic.data)
                        thumbnail_path = thumb_file

                # 2. MP3
                elif isinstance(audio, mutagen.mp3.MP3) or isinstance(audio, mutagen.id3.ID3FileType):
                    id3 = getattr(audio, "tags", None) or audio
                    if id3:
                        if "TIT2" in id3:
                            default_title = str(id3["TIT2"])
                        if "TPE1" in id3:
                            default_performer = str(id3["TPE1"])
                        if "TALB" in id3:
                            default_album = str(id3["TALB"])

                        for tag in id3.values():
                            if isinstance(tag, APIC):
                                thumb_file = file_path.with_suffix(".thumb.jpg")
                                thumb_file.write_bytes(tag.data)
                                thumbnail_path = thumb_file
                                break

                # 3. MP4 / M4A
                elif isinstance(audio, MP4):
                    tags = audio.tags or {}
                    if "\xa9nam" in tags and tags["\xa9nam"]:
                        default_title = tags["\xa9nam"][0]
                    if "\xa9ART" in tags and tags["\xa9ART"]:
                        default_performer = tags["\xa9ART"][0]
                    if "\xa9alb" in tags and tags["\xa9alb"]:
                        default_album = tags["\xa9alb"][0]
                    if "covr" in tags and tags["covr"]:
                        cov = tags["covr"][0]
                        thumb_file = file_path.with_suffix(".thumb.jpg")
                        thumb_file.write_bytes(bytes(cov))
                        thumbnail_path = thumb_file

                # 4. OGG / OPUS
                elif isinstance(audio, (OggVorbis, OggOpus)):
                    if "title" in audio and audio["title"]:
                        default_title = audio["title"][0]
                    if "artist" in audio and audio["artist"]:
                        default_performer = audio["artist"][0]
                    if "album" in audio and audio["album"]:
                        default_album = audio["album"][0]
                    # Check METADATA_BLOCK_PICTURE
                    if "metadata_block_picture" in audio:
                        import base64
                        try:
                            raw = base64.b64decode(audio["metadata_block_picture"][0])
                            pic = Picture(raw)
                            thumb_file = file_path.with_suffix(".thumb.jpg")
                            thumb_file.write_bytes(pic.data)
                            thumbnail_path = thumb_file
                        except Exception:
                            pass

        except Exception:
            # Fallback to filename splitting: "Artist - Title"
            if " - " in stem:
                parts = stem.split(" - ", 1)
                default_performer = parts[0].strip()
                default_title = parts[1].strip()

        # Check for standalone cover.jpg / folder.jpg in the same directory
        if not thumbnail_path or not thumbnail_path.exists():
            for img_name in ["cover.jpg", "folder.jpg", "cover.png", "folder.png"]:
                candidate = file_path.parent / img_name
                if candidate.exists():
                    thumbnail_path = candidate
                    break

        return AudioMetadata(
            title=default_title,
            performer=default_performer,
            album=default_album,
            duration=duration,
            thumbnail_path=thumbnail_path
        )

    @staticmethod
    def compress_to_mp3(file_path: Path, target_bitrate: str = "320k") -> Optional[Path]:
        """
        Compresses an audio file to MP3 using ffmpeg if it exceeds 50MB.
        Returns the path to the compressed file, or None if ffmpeg fails.
        """
        out_path = file_path.with_suffix(".compressed.mp3")
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(file_path),
                "-codec:a", "libmp3lame",
                "-b:a", target_bitrate,
                "-map_metadata", "0",
                "-id3v2_version", "3",
                str(out_path)
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=180
            )
            if result.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                return out_path
        except Exception:
            pass
        return None
