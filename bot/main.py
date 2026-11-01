import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from bot.config import config
from bot.services.telethon_client import get_client, start_client_interactive
from bot.services.uploader import TelethonUploader
from bot.handlers.userbot_handlers import register_userbot_handlers

console = Console()


async def main():
    console.print(
        Panel(
            "[bold cyan]FlacDL Telethon MTProto Userbot[/bold cyan]\n"
            "[dim]Direct High-Speed Large File Streaming (Up to 2GB) from Google Cloud Shell[/dim]\n\n"
            f"• [white]API ID:[/] [yellow]{config.API_ID}[/]\n"
            f"• [white]Session Path:[/] [green]{config.session_file_path}.session[/]\n"
            f"• [white]Command Prefix:[/] [cyan]{config.COMMAND_PREFIX}[/]\n"
            f"• [white]Max MTProto File Size:[/] [magenta]2,000 MB (2 GB)[/]",
            title="[bold green]System Starting[/]",
            border_style="cyan"
        )
    )

    client = get_client()

    # Start client (handles initial phone/code/2FA login or uses existing session)
    await start_client_interactive(client)

    # CLI mode check: direct upload from terminal
    # Example: python -m bot.main upload /path/to/song.flac [chat_id/username]
    if len(sys.argv) >= 3 and sys.argv[1].lower() == "upload":
        target_file = Path(sys.argv[2]).expanduser()
        target_chat = sys.argv[3] if len(sys.argv) >= 4 else "me"  # default to 'me' (Saved Messages)

        console.print(f"[bold yellow]Direct CLI upload mode:[/] {target_file} -> {target_chat}")
        uploader = TelethonUploader(client)
        try:
            await uploader.upload_file(
                entity=target_chat,
                file_path=target_file,
                show_terminal_progress=True
            )
            console.print("[bold green]✅ CLI Upload completed successfully![/]")
        except Exception as e:
            console.print(f"[bold red]❌ CLI Upload failed: {e}[/]")
        finally:
            await client.disconnect()
            return

    # Userbot Listener Daemon mode
    register_userbot_handlers(client)
    console.print("[bold green]📡 Userbot is listening for commands and music links in Telegram...[/]")
    console.print(f"[dim]Send [cyan]{config.COMMAND_PREFIX}help[/] in Saved Messages or any chat to see available commands.[/dim]\n")

    try:
        await client.run_until_disconnected()
    except (KeyboardInterrupt, SystemExit):
        console.print("[yellow]Userbot stopped by user.[/]")
    finally:
        if client.is_connected():
            await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
