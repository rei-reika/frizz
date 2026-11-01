from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from bot.config import config


class AccessControlMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None

        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is not None:
            if not config.is_user_allowed(user_id):
                if isinstance(event, Message):
                    await event.answer(
                        f"⛔ <b>Access Restricted</b>\n\n"
                        f"This bot is currently private.\n"
                        f"Your Telegram User ID is: <code>{user_id}</code>\n"
                        f"Provide this ID to the bot administrator to request access.",
                        parse_mode="HTML"
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer("⛔ Access restricted for your account.", show_alert=True)
                return

        return await handler(event, data)
