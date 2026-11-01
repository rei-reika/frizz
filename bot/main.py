import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

from bot.config import config
from bot.database import db
from bot.middlewares import AccessControlMiddleware
from bot.handlers import register_handlers
from bot.services import init_queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("flacdl_bot")


async def set_default_commands(bot: Bot):
    """Set default slash commands in Telegram menu."""
    commands = [
        BotCommand(command="track", description="Download single track (or text query)"),
        BotCommand(command="album", description="Download full album"),
        BotCommand(command="playlist", description="Download public streaming playlist"),
        BotCommand(command="settings", description="Audio format, bitrate & service preferences"),
        BotCommand(command="help", description="Supported services and instructions"),
        BotCommand(command="status", description="Server resources and statistics")
    ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    except Exception as e:
        logger.warning(f"Could not set default commands: {e}")


async def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ":
        logger.error(
            "CRITICAL: BOT_TOKEN is not set!\n"
            "Please copy .env.example to .env and configure your BOT_TOKEN from @BotFather."
        )
        sys.exit(1)

    # Initialize Database
    logger.info("Initializing SQLite database...")
    await db.init()

    # Configure session and Bot instance
    session = None
    if config.LOCAL_BOT_API_URL:
        logger.info(f"Using custom Local Telegram Bot API server: {config.LOCAL_BOT_API_URL}")
        custom_server = TelegramAPIServer.from_base(config.LOCAL_BOT_API_URL)
        session = AiohttpSession(api=custom_server)

    bot = Bot(
        token=config.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    # Middlewares
    dp.message.middleware(AccessControlMiddleware())
    dp.callback_query.middleware(AccessControlMiddleware())

    # Handlers
    register_handlers(dp)

    # Start Queue Manager
    logger.info("Starting download queue manager...")
    queue_mgr = init_queue(bot)

    # Bot Commands
    await set_default_commands(bot)

    logger.info("FlacDL Telegram Bot is up and running! Starting polling...")

    try:
        # Delete pending webhook updates and start polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down bot...")
        await queue_mgr.stop()
        await bot.session.close()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot process exited.")
