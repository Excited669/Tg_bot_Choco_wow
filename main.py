import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN # Убедитесь, что BOT_TOKEN определен в config.py
from database.database import Database # Импортируем КЛАСС Database
from handlers import user_handlers, admin_handlers

# Настройка логирования для всего приложения
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    # 1. Инициализация базы данных: создаем экземпляр и настраиваем таблицы
    db_instance = Database() # Создаем объект базы данных
    await db_instance.connect() # Устанавливаем соединение с БД
    await db_instance.setup_database() # Создаем таблицы, если их нет
    logging.info("База данных инициализирована: таблица 'participants' проверена/создана.")

    # 2. Инициализация бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()

    # 3. Регистрация роутеров
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    # 4. Запуск бота
    try:
        logging.info("Запускаем опрос бота %s", await bot.get_me())
        # Самое важное: передаем объект db_instance в контекст диспетчера.
        # Теперь он будет доступен в хендлерах как аргумент с тем же именем.
        await dp.start_polling(bot, db_instance=db_instance)
    finally:
        # Убедимся, что соединение с сессией бота и с базой данных закрываются
        await bot.session.close()
        await db_instance.close() # Закрываем соединение с базой данных при завершении работы

if __name__ == "__main__":
    asyncio.run(main())