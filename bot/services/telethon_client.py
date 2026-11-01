import os
import sys
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from rich.console import Console
from rich.panel import Panel

from bot.config import config

console = Console()


def get_client() -> TelegramClient:
    """
    Creates TelegramClient with session path strictly pinned to persistent $HOME directory.
    In Google Cloud Shell, only files under $HOME persist across VM restarts.
    """
    if not config.API_ID or not config.API_HASH:
        console.print(
            Panel.fit(
                "[bold red]CRITICAL: API_ID or API_HASH is missing![/]\n\n"
                "Please configure [yellow].env[/] with your Telegram credentials from:\n"
                "[link=https://my.telegram.org]https://my.telegram.org[/] (API development tools)\n\n"
                "Example:\n"
                "  API_ID=12345678\n"
                "  API_HASH=0123456789abcdef0123456789abcdef",
                title="[red]Authentication Error[/]"
            )
        )
        sys.exit(1)

    session_path = config.session_file_path
    console.print(f"[dim]📁 Session file target: [cyan]{session_path}.session[/][/dim]")

    # Initialize Telethon Client
    client = TelegramClient(
        session=str(session_path),
        api_id=config.API_ID,
        api_hash=config.API_HASH
    )
    return client


async def start_client_interactive(client: TelegramClient) -> None:
    """
    Start the client, performing phone number login if not already authenticated.
    Once authenticated, Telethon persists the session file to disk.
    """
    await client.connect()

    # Check if already authorized from existing persistent session
    if not await client.is_user_authorized():
        if config.PHONE_NUMBER and config.PHONE_NUMBER.strip():
            phone = config.PHONE_NUMBER.strip()
        else:
            phone = lambda: input("Please enter your phone number (+countrycode): ")

        await client.start(phone=phone)

    me = await client.get_me()
    username = f"@{me.username}" if me.username else "No username"
    session_file = f"{config.session_file_path}.session"

    console.print(
        Panel(
            f"[bold green]✅ Telethon Userbot Successfully Authenticated![/]\n\n"
            f"👤 [bold white]Logged in as:[/] {me.first_name} ({username})\n"
            f"🆔 [bold white]User ID:[/] [cyan]{me.id}[/]\n"
            f"📱 [bold white]Phone:[/] {me.phone}\n"
            f"💾 [bold white]Persistent Session:[/] [yellow]{session_file}[/]\n\n"
            f"[italic dim]Session is stored inside $HOME and will remain active across Cloud Shell restarts.[/]",
            title="[bold cyan]Google Cloud Shell MTProto Userbot[/]",
            border_style="green"
        )
    )
