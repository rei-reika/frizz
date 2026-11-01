from aiogram import Dispatcher
from .common import router as common_router
from .settings import router as settings_router
from .download import router as download_router
from .admin import router as admin_router


def register_handlers(dp: Dispatcher):
    dp.include_router(common_router)
    dp.include_router(settings_router)
    dp.include_router(admin_router)
    dp.include_router(download_router)  # Download router placed last to catch general text
