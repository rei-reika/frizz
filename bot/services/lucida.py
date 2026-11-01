import asyncio
import os
import shutil
import re
from pathlib import Path
from typing import Optional, Callable, Awaitable, List
from bot.config import config


class LucidaRunner:
    def __init__(self):
        self._cached_binary: Optional[str] = None

    def get_binary(self) -> str:
        """Find the executable binary for lucida / lucidadl."""
        if self._cached_binary:
            return self._cached_binary

        if config.LUCIDA_BIN != "auto":
            if shutil.which(config.LUCIDA_BIN) or Path(config.LUCIDA_BIN).exists():
                self._cached_binary = config.LUCIDA_BIN
                return self._cached_binary

        candidates = [
            "lucida",
            "lucidadl",
            str(Path.home() / ".local/bin/lucida"),
            str(Path.home() / ".local/bin/lucidadl"),
            "/usr/local/bin/lucida",
            "/usr/local/bin/lucidadl"
        ]

        for cand in candidates:
            if shutil.which(cand) or Path(cand).is_file():
                self._cached_binary = cand
                return self._cached_binary

        # Default fallback
        self._cached_binary = "lucida"
        return self._cached_binary

    async def run_download(
        self,
        command_type: str,
        target: str,
        out_dir: Path,
        format_type: str = "flac",
        bitrate: str = "320k",
        service: str = "default",
        progress_cb: Optional[Callable[[str], Awaitable[None]]] = None,
        cancel_event: Optional[asyncio.Event] = None
    ) -> List[Path]:
        """
        Execute lucida download for track, album, or playlist.
        Returns list of downloaded audio files.
        """
        binary = self.get_binary()
        out_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            binary,
            command_type,  # 'track', 'album', or 'playlist'
            target,
            "--out", str(out_dir),
            "--flat",
            "--force"
        ]

        # Transcoding options
        if format_type and format_type.lower() != "flac":
            cmd.extend(["--to", format_type.lower()])
            if bitrate:
                cmd.extend(["--bitrate", bitrate])

        # Specific streaming service
        if service and service.lower() != "default":
            cmd.extend(["-s", service.lower()])

        env = os.environ.copy()
        # Add local bins to PATH
        local_bin = str(Path.home() / ".local/bin")
        if local_bin not in env.get("PATH", ""):
            env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"

        if progress_cb:
            await progress_cb("🔍 Initializing Lucida & searching provider...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env
        )

        output_lines: List[str] = []
        last_progress_text = ""

        async def read_stream():
            nonlocal last_progress_text
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                if not decoded:
                    continue
                output_lines.append(decoded)

                # Clean ANSI escape sequences
                clean_line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', decoded).strip()
                if not clean_line:
                    continue

                # Progress parsing heuristics
                low = clean_line.lower()
                status_update = None
                if "downloading" in low:
                    status_update = f"📥 {clean_line}"
                elif "transcoding" in low or "converting" in low:
                    status_update = f"🔄 {clean_line}"
                elif "fetching" in low or "resolving" in low or "searching" in low:
                    status_update = f"🔍 {clean_line}"
                elif "done" in low or "completed" in low or "saved" in low:
                    status_update = f"✅ {clean_line}"
                elif "cloudflare" in low or "turnstile" in low:
                    status_update = f"⚠️ Cloudflare verification notice..."

                if status_update and status_update != last_progress_text and progress_cb:
                    last_progress_text = status_update
                    try:
                        await progress_cb(status_update)
                    except Exception:
                        pass

        stream_task = asyncio.create_task(read_stream())

        try:
            # Monitor process with cancellation and timeout
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(process.wait()),
                    asyncio.create_task(cancel_event.wait()) if cancel_event else asyncio.create_task(asyncio.sleep(float('inf')))
                ],
                timeout=config.DOWNLOAD_TIMEOUT_SECONDS,
                return_when=asyncio.FIRST_COMPLETED
            )

            # Check if cancelled
            if cancel_event and cancel_event.is_set():
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    process.kill()
                await stream_task
                raise asyncio.CancelledError("Download cancelled by user.")

            # Check if timed out
            if not done:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    process.kill()
                await stream_task
                raise TimeoutError(f"Download timed out after {config.DOWNLOAD_TIMEOUT_SECONDS}s.")

            await stream_task

        finally:
            if process.returncode is None:
                try:
                    process.kill()
                except Exception:
                    pass

        # Scan directory for generated audio files
        audio_extensions = {".flac", ".mp3", ".m4a", ".aac", ".opus", ".ogg", ".wav"}
        downloaded_files = [
            f for f in out_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in audio_extensions
        ]

        if process.returncode != 0 and not downloaded_files:
            error_summary = "\n".join(output_lines[-10:])
            if "cloudflare" in error_summary.lower() or "setup" in error_summary.lower():
                raise RuntimeError(
                    "Lucida requires initial setup/Cloudflare clearance.\n"
                    "Run <code>lucida setup</code> on the server or run /setup_help for instructions."
                )
            raise RuntimeError(f"Lucida command failed (exit code {process.returncode}):\n{error_summary}")

        return downloaded_files

    async def run_doctor(self, live: bool = True) -> str:
        """Run lucida doctor to test system configuration."""
        binary = self.get_binary()
        cmd = [binary, "doctor"]
        if live:
            cmd.append("--live")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=45.0)
            text = stdout.decode("utf-8", errors="replace")
            # Strip ansi
            clean_text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
            return clean_text.strip()
        except Exception as e:
            return f"Error executing '{' '.join(cmd)}': {str(e)}"


lucida_runner = LucidaRunner()
