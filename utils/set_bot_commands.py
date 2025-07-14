# utils/set_bot_commands.py

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat

from config import MAIN_ADMIN_ID

async def set_admin_commands(bot: Bot, admin_ids: list[int]):
    """
    Устанавливает разные наборы команд для главного админа и обычных админов.
    """
    # Общие команды для всех админов
    common_commands = [
        BotCommand(command="get_users_db", description="Выгрузить базу участников (CSV)"),
        BotCommand(command="send_raffle_reminder", description="Отправить напоминание о розыгрыше"),
        BotCommand(command="send_results", description="Отправить результаты розыгрыша")
    ]

    # Команды только для главного админа
    main_admin_commands = common_commands + [
        BotCommand(command="add_admin", description="➕ Добавить администратора"),
        BotCommand(command="remove_admin", description="➖ Удалить администратора"),
        BotCommand(command="list_admins", description="👥 Показать список администраторов")
    ]

    for admin_id in admin_ids:
        try:
            # Устанавливаем расширенный набор команд для главного админа
            if admin_id == MAIN_ADMIN_ID:
                await bot.set_my_commands(commands=main_admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
            # Устанавливаем обычный набор для всех остальных
            else:
                await bot.set_my_commands(commands=common_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            print(f"Не удалось установить команды для администратора {admin_id}: {e}")