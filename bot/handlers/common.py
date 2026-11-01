from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from bot.config import config
from bot.utils.helpers import escape_html

router = Router(name="common")


@router.message(CommandStart())
async def handle_start(message: Message):
    user_name = message.from_user.first_name if message.from_user else "Music Lover"
    welcome_text = (
        f"👋 <b>Welcome, {escape_html(user_name)}!</b>\n\n"
        f"I am your high-fidelity <b>FlacDL Music Downloader Bot</b>.\n"
        f"I can fetch lossless (FLAC) and high-bitrate audio from leading streaming services "
        f"via <b>lucida.to</b>.\n\n"
        f"<b>🚀 How to use:</b>\n"
        f"• Simply paste any track, album, or playlist link (Spotify, Apple Music, Deezer, Tidal, Qobuz, etc.).\n"
        f"• Or type a song title directly, e.g.: <code>Adele - Easy On Me</code>\n"
        f"• Or use commands: /track, /album, /playlist\n\n"
        f"<b>⚙️ Quick Commands:</b>\n"
        f"/settings - Change audio format (FLAC, MP3 320k, OPUS) & service\n"
        f"/help - Detailed guide & supported platforms\n"
        f"/status - Check server & bot status\n"
    )
    if message.from_user and config.is_admin(message.from_user.id):
        welcome_text += "\n<i>🛡️ Admin commands: /doctor, /setup_help, /status, /broadcast</i>\n"

    await message.answer(welcome_text, parse_mode="HTML")


@router.message(Command("help"))
async def handle_help(message: Message):
    help_text = (
        f"📖 <b>FlacDL Bot Help Guide</b>\n\n"
        f"<b>1. Supported Music Platforms:</b>\n"
        f"• 🟢 <b>Spotify</b> (Tracks, Albums, Playlists)\n"
        f"• 🍎 <b>Apple Music</b> (Tracks, Albums, Playlists)\n"
        f"• 🟣 <b>Deezer</b> (Tracks, Albums, Playlists)\n"
        f"• ⬛ <b>TIDAL</b> (Tracks, Albums, Playlists)\n"
        f"• 🔵 <b>Qobuz</b> (Tracks, Albums, Playlists - Lossless Hi-Res!)\n"
        f"• 🟠 <b>SoundCloud</b> (Tracks, Sets)\n"
        f"• 📦 <b>Amazon Music</b> (Tracks, Albums, Playlists)\n"
        f"• ▶️ <b>YouTube Music</b> (Tracks, Playlists)\n\n"
        f"<b>2. Commands:</b>\n"
        f"• <code>/track &lt;link or title&gt;</code> — Download a single track\n"
        f"• <code>/album &lt;link or query&gt;</code> — Download a full album\n"
        f"• <code>/playlist &lt;link&gt;</code> — Download an entire public playlist\n"
        f"• <code>/settings</code> — Configure audio format, bitrate, provider\n"
        f"• <code>/status</code> — Server resources and download statistics\n\n"
        f"<b>3. Direct Sending:</b>\n"
        f"You don't even need commands! Just paste any link into the chat and the bot "
        f"will automatically determine if it's a track, album, or playlist.\n\n"
        f"<b>4. Telegram 50MB Upload Limit Note:</b>\n"
        f"By default, Telegram cloud bots allow up to 50MB per file. If a 24-bit FLAC exceeds "
        f"50MB, the bot will automatically convert it to a pristine 320kbps MP3 so you can still receive it."
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("about"))
async def handle_about(message: Message):
    about_text = (
        f"ℹ️ <b>About FlacDL Bot</b>\n\n"
        f"• Powered by: <b>LucidaDL</b> & <b>lucida.to</b>\n"
        f"• Framework: <b>aiogram 3.x</b> (Python 3.13)\n"
        f"• Lossless FLAC, MP3 320k, M4A, OPUS transcoding supported\n"
        f"• Metadata & Cover Art embedding enabled\n"
    )
    await message.answer(about_text, parse_mode="HTML")
