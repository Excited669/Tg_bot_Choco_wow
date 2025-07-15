# utils/set_bot_commands.py

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat

async def set_bot_commands(bot: Bot, admin_ids: list[int]):
    """
    Устанавливает единую команду /admin для всех администраторов.
    """
    admin_command = [
        BotCommand(command="admin", description="Открыть панель администратора")
    ]

    # Сначала очищаем команды для всех, на случай если кто-то был разжалован
    # await bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())

    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(commands=admin_command, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            print(f"Не удалось установить команды для администратора {admin_id}: {e}")