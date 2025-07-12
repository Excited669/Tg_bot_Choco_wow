# handlers/admin_handlers.py

import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command, BaseFilter
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, BufferedInputFile  # Используем BufferedInputFile
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime  # Импортируем datetime для даты/времени в имени файла

from config import ADMIN_IDS
from database.database import Database as DB
from keyboards.inline import get_admin_keyboard
from utils.email_sender import send_email_with_photos
from utils.export_data import generate_participants_csv  # Импортируем утилиту для генерации CSV

router = Router()

logger = logging.getLogger(__name__)


# Фильтр для проверки, является ли пользователь админом
class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMIN_IDS


# Функция для отправки заявки админам
async def send_submission_to_admin(bot: Bot, submission_id: int, user_id: int, username: str, collection_photo: str,
                                   receipt_photo: str):
    caption_for_text_message = (
        f"Новая заявка №{submission_id}\n"
        f"От: @{username} (ID: {user_id})\n"
        f"Выберите действие:"
    )
    keyboard = get_admin_keyboard(submission_id, user_id)

    media_group = [
        InputMediaPhoto(media=collection_photo, caption="Фото коллекции"),
        InputMediaPhoto(media=receipt_photo, caption="Фото чеков")
    ]

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_media_group(admin_id, media=media_group)
            await bot.send_message(admin_id, caption_for_text_message, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")

    # Отправляем письмо с фото админам (если настроено)
    await send_email_with_photos(
        bot=bot,
        caption=f"Новая заявка №{submission_id} от @{username} (ID: {user_id})",
        file_ids=[collection_photo, receipt_photo]
    )


@router.callback_query(F.data.startswith("admin:"))
async def process_admin_action(callback: CallbackQuery, bot: Bot, db_instance: DB):
    await callback.answer("Обрабатываю запрос...")

    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    _, action, sub_id, user_id_str = callback.data.split(":")
    submission_id = int(sub_id)
    user_id = int(user_id_str)

    actions = {
        "approve": ("approved", "Вы стали участником розыгрыша!"),
        "bonus": ("bonus", "Поздравляем! Вам доступен гарантированный приз!"),
        "reject": ("rejected", "Ваше участие не подтверждено. Попробуйте снова: /start")
    }

    if action in actions:
        status, text_for_user = actions[action]
        await db_instance.update_status(user_id, status)
        try:
            await bot.send_message(user_id, text_for_user)
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
            await bot.send_message(callback.from_user.id, f"⚠️ Не удалось уведомить пользователя {user_id}: {e}")

        status_text = {"approve": "ПОДТВЕРЖДЕНА", "bonus": "ПОДТВЕРЖДЕНА С БОНУСОМ", "reject": "ОТКЛОНЕНА"}

        try:
            await callback.message.edit_text(
                text=f"✅ Заявка №{submission_id} {status_text[action]}.",
                reply_markup=None
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                logger.info(f"Сообщение админа уже было изменено или не требует изменений для заявки {submission_id}.")
            else:
                raise e
        except Exception as e:
            logger.error(f"Неизвестная ошибка при редактировании сообщения админа для заявки {submission_id}: {e}")


# --- КОМАНДА: ЭКСПОРТ БАЗЫ ДАННЫХ ---
@router.message(Command("get_users_db"), IsAdmin())
async def cmd_get_users_db(message: Message, bot: Bot, db_instance: DB):
    await message.answer("Подготовка данных пользователей...")

    try:
        # Получаем данные из БД (уже без address, phone, full_name благодаря изменению в database.py)
        column_names, rows = await db_instance.get_all_participants_data()

        if not rows:
            await message.answer("В базе данных пока нет участников.")
            return

        # Генерируем CSV-файл в памяти, передавая объект bot для получения file_path
        csv_buffer = await generate_participants_csv(column_names, rows, bot)

        # Формируем имя файла с датой и временем
        now = datetime.now()
        # Пример: "11 07 2025 16_53" (день месяц год часы_минуты)
        filename_timestamp = now.strftime("%d %m %Y %H_%M")
        file_name = f"participants_{filename_timestamp}.csv"

        await bot.send_document(
            chat_id=message.chat.id,
            document=BufferedInputFile(csv_buffer.getvalue(), filename=file_name),
            # Используем BufferedInputFile и новое имя файла
            caption="Вот база данных всех участников:"
        )
        await message.answer("База данных пользователей отправлена.")

    except Exception as e:
        await message.answer(f"Произошла ошибка при получении данных: {e}")
        logger.error(f"Ошибка при экспорте данных: {e}")


@router.message(Command("sendreminder"), IsAdmin())
async def cmd_send_reminder(message: Message, bot: Bot, db_instance: DB):
    users = await db_instance.get_approved_users()
    text = "Напоминаем, что уже сегодня пройдет розыгрыш призов! 🏆"
    count = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Не удалось отправить напоминание пользователю {user_id}: {e}")
            pass
    await message.answer(f"Рассылка завершена. Отправлено {count} сообщений.")