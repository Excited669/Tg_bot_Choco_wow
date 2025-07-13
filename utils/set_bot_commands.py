from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat

async def set_admin_commands(bot: Bot, admin_ids: list[int]):
    """Устанавливает список команд для администраторов."""
    commands = [
        BotCommand(command="get_users_db", description="Выгрузить базу участников (CSV)"),
        BotCommand(command="send_raffle_reminder", description="Отправить напоминание о розыгрыше"),
        BotCommand(command="send_results", description="Отправить результаты розыгрыша")
    ]
    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(commands=commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            print(f"Could not set commands for admin {admin_id}: {e}")