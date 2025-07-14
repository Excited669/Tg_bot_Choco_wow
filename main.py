# main.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, MAIN_ADMIN_ID
from database.database import Database
from handlers import user_handlers, admin_handlers
from utils.set_bot_commands import set_admin_commands

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    storage = MemoryStorage()

    db_instance = Database()
    await db_instance.connect()
    await db_instance.setup_database()
    await db_instance.add_admin(MAIN_ADMIN_ID)
    logger.info("База данных инициализирована.")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.start()

    dp = Dispatcher(storage=storage, db_instance=db_instance, scheduler=scheduler)

    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    all_admins = await db_instance.get_all_admins()
    if MAIN_ADMIN_ID not in all_admins:
        all_admins.append(MAIN_ADMIN_ID)
    await set_admin_commands(bot, all_admins)
    logger.info("Команды для администраторов установлены.")

    try:
        logger.info("Запускаем опрос бота...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await db_instance.close()
        scheduler.shutdown()
        logger.info("Работа бота и соединение с БД завершены.")


if __name__ == "__main__":
    asyncio.run(main())