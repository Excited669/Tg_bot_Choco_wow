import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
from database.database import Database
from handlers import user_handlers, admin_handlers
from utils.set_bot_commands import set_admin_commands

# Настройка логирования для всего приложения
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    # 1. Инициализация хранилища для FSM
    storage = MemoryStorage()

    # 2. Инициализация базы данных
    db_instance = Database()
    await db_instance.connect()
    await db_instance.setup_database()
    logger.info("База данных инициализирована.")

    # 3. Инициализация бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=storage)

    # 4. Регистрация роутеров
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    # 5. Установка команд для админов
    await set_admin_commands(bot, ADMIN_IDS)
    logger.info("Команды для администраторов установлены.")

    # 6. Запуск бота
    try:
        logger.info("Запускаем опрос бота %s", await bot.get_me())
        # Передаем объект db_instance в контекст диспетчера
        await dp.start_polling(bot, db_instance=db_instance)
    finally:
        await bot.session.close()
        await db_instance.close()
        logger.info("Работа бота и соединение с БД завершены.")

if __name__ == "__main__":
    asyncio.run(main())