import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command, BaseFilter, StateFilter
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, BufferedInputFile
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from datetime import datetime

from config import ADMIN_IDS
from database.database import Database as DB
from keyboards.inline import get_admin_keyboard, get_rejection_keyboard
from utils.email_sender import send_email_with_files
from utils.export_data import generate_participants_csv
from states import AdminFSM

router = Router()
logger = logging.getLogger(__name__)


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMIN_IDS


async def send_submission_to_admin(bot: Bot, submission_id: int, user_id: int, username: str,
                                   collection_photos: list[str], receipt_files: list[str]):
    caption = (
        f"🔥 Новая заявка №{submission_id}\n"
        f"От: @{username} (ID: {user_id})"
    )
    keyboard = get_admin_keyboard(submission_id, user_id)
    all_files = collection_photos + receipt_files

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, caption)

            photo_media_group = []
            for photo_id in collection_photos:
                photo_media_group.append(InputMediaPhoto(media=photo_id))

            if photo_media_group:
                # Split into chunks of 10 for media group limit
                for i in range(0, len(photo_media_group), 10):
                    await bot.send_media_group(admin_id, media=photo_media_group[i:i + 10])

            # Send receipt files (can be photo or pdf)
            for file_id in receipt_files:
                try:
                    file_info = await bot.get_file(file_id)
                    if file_info.file_path.endswith('.pdf'):
                        await bot.send_document(admin_id, document=file_id, caption="📄 Чек (PDF)")
                    else:
                        await bot.send_photo(admin_id, photo=file_id, caption="📄 Чек (Фото)")
                except Exception as e:
                    logger.error(f"Could not send file {file_id} to admin {admin_id}: {e}")

            await bot.send_message(admin_id, "Выберите действие:", reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Не удалось отправить заявку админу {admin_id}: {e}")

    await send_email_with_files(
        bot=bot,
        caption=f"Новая заявка №{submission_id} от @{username} (ID: {user_id})",
        file_ids=all_files
    )


@router.callback_query(F.data.startswith("admin:"))
async def process_admin_action(callback: CallbackQuery, bot: Bot, db_instance: DB, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    _, action, sub_id_str, user_id_str = callback.data.split(":")
    submission_id = int(sub_id_str)
    user_id = int(user_id_str)

    if action == "reject":
        await callback.answer()
        await state.update_data(submission_id=submission_id, user_id=user_id,
                                admin_message_id=callback.message.message_id)
        await state.set_state(AdminFSM.reject_reason)
        await callback.message.edit_text(
            f"Отклонить заявку №{submission_id} от пользователя ID {user_id}?\n\n"
            "Вы можете отправить причину отклонения в следующем сообщении или отклонить без указания причины.",
            reply_markup=get_rejection_keyboard()
        )
        return

    await callback.answer("Обрабатываю запрос...")

    actions = {
        "approve": ("approved", "Вы стали участником розыгрыша, следите за новостями в нашей группе!"),
        "bonus": ("bonus",
                  "Поздравляем! Вам доступен гарантированный приз! Просьба уточнить данные для отправки: Адрес, ФИО, номер телефона.")
    }

    if action in actions:
        status, text_for_user = actions[action]
        await db_instance.update_status(user_id, status)
        try:
            await bot.send_message(user_id, text_for_user)
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
            await bot.send_message(callback.from_user.id, f"⚠️ Не удалось уведомить пользователя {user_id}: {e}")

        status_text = {"approve": "✅ ПОДТВЕРЖДЕНА", "bonus": "🎁 ПОДТВЕРЖДЕНА С БОНУСОМ"}
        try:
            # Edit original message with action buttons
            original_message_with_buttons = callback.message
            await original_message_with_buttons.edit_reply_markup(reply_markup=None)
            await bot.edit_message_text(
                text=f"Заявка №{submission_id} {status_text[action]}.",
                chat_id=callback.from_user.id,
                message_id=original_message_with_buttons.message_id - 1,
                # Assumes caption is the message before keyboard
            )

        except Exception as e:
            logger.warning(f"Could not edit admin message for submission {submission_id}: {e}")
            await callback.message.edit_text(f"Заявка №{submission_id} {status_text[action]}.")


@router.message(AdminFSM.reject_reason, F.text)
async def process_rejection_reason(message: Message, state: FSMContext, bot: Bot, db_instance: DB):
    reason = message.text
    data = await state.get_data()
    user_id = data['user_id']
    submission_id = data['submission_id']
    admin_message_id = data['admin_message_id']

    await db_instance.update_status(user_id, "rejected")
    rejection_message = (
        "Ой, ваше участие в розыгрыше не подтверждено.\n\n"
        f"<b>Причина:</b> {reason}\n\n"
        "Можете повторно прислать нам данные для проверки, начав с команды /start."
    )
    try:
        await bot.send_message(user_id, rejection_message)
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_id} о причине отклонения: {e}")

    await message.bot.edit_message_text(
        f"❌ Заявка №{submission_id} ОТКЛОНЕНА. Причина указана.",
        chat_id=message.from_user.id,
        message_id=admin_message_id,
        reply_markup=None
    )
    await state.clear()


@router.callback_query(AdminFSM.reject_reason, F.data == "reject_no_reason")
async def process_rejection_no_reason(callback: CallbackQuery, state: FSMContext, bot: Bot, db_instance: DB):
    await callback.answer()
    data = await state.get_data()
    user_id = data['user_id']
    submission_id = data['submission_id']

    await db_instance.update_status(user_id, "rejected")
    rejection_message = "Ой, ваше участие в розыгрыше не подтверждено. Возможно, фото коллекции или чеков были нечеткими. Можете повторно прислать нам данные для проверки, начав с команды /start."
    try:
        await bot.send_message(user_id, rejection_message)
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_id} об отклонении: {e}")

    await callback.message.edit_text(
        f"❌ Заявка №{submission_id} ОТКЛОНЕНА. Без указания причины.",
        reply_markup=None
    )
    await state.clear()


@router.message(Command("get_users_db"), IsAdmin())
async def cmd_get_users_db(message: Message, bot: Bot, db_instance: DB):
    await message.answer("Подготовка данных пользователей...")
    try:
        column_names, rows = await db_instance.get_all_participants_data()
        if not rows:
            await message.answer("В базе данных пока нет участников.")
            return

        csv_buffer = await generate_participants_csv(column_names, rows, bot)
        filename_timestamp = datetime.now().strftime("%d.%m.%Y_%H:%M")
        file_name = f"database_chocowow_{filename_timestamp}.csv"

        await bot.send_document(
            chat_id=message.chat.id,
            document=BufferedInputFile(csv_buffer.getvalue(), filename=file_name),
            caption="Вот база данных всех участников:"
        )
    except Exception as e:
        await message.answer(f"Произошла ошибка при получении данных: {e}")
        logger.error(f"Ошибка при экспорте данных: {e}")


@router.message(Command("send_raffle_reminder"), IsAdmin())
async def cmd_send_raffle_reminder(message: Message, bot: Bot, db_instance: DB):
    users = await db_instance.get_approved_users()
    text = "Напоминаем, что уже сегодня пройдет розыгрыш призов! 🏆 Следите за новостями в нашем тг канале ______"
    count = 0
    await message.answer(f"Начинаю рассылку напоминаний для {len(users)} пользователей...")
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Не удалось отправить напоминание пользователю {user_id}: {e}")
    await message.answer(f"Рассылка завершена. Отправлено {count} сообщений.")


@router.message(Command("send_results"), IsAdmin())
async def cmd_send_results(message: Message, bot: Bot, db_instance: DB, command: Command):
    # command.args will contain the text after the command, e.g., the link
    results_link = command.args
    if not results_link:
        await message.answer(
            "Пожалуйста, укажите ссылку на результаты после команды. \nПример: `/send_results https://t.me/your_channel/123`")
        return

    users = await db_instance.get_approved_users()
    text = f"Розыгрыш завершен, результаты доступны по ссылке: {results_link}"
    count = 0
    await message.answer(f"Начинаю рассылку результатов для {len(users)} пользователей...")
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Не удалось отправить результаты пользователю {user_id}: {e}")
    await message.answer(f"Рассылка результатов завершена. Отправлено {count} сообщений.")