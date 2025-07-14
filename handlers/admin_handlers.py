# handlers/admin_handlers.py

import asyncio
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command, BaseFilter, StateFilter, CommandObject
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, BufferedInputFile
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import MAIN_ADMIN_ID
from database.database import Database as DB
from keyboards.inline import get_admin_keyboard, get_rejection_keyboard, get_schedule_keyboard
from utils.email_sender import send_email_with_files
from utils.export_data import generate_participants_csv
from states import AdminFSM

router = Router()
logger = logging.getLogger(__name__)


# --- Фильтры доступа ---
class IsAdmin(BaseFilter):
    async def __call__(self, message: Message | CallbackQuery, db_instance: DB) -> bool:
        all_admins = await db_instance.get_all_admins()
        all_admins.append(MAIN_ADMIN_ID)
        return message.from_user.id in all_admins


class IsMainAdmin(BaseFilter):
    async def __call__(self, message: Message, db_instance: DB) -> bool:
        return message.from_user.id == MAIN_ADMIN_ID


# --- Отправка заявки админам ---
async def send_submission_to_admin(bot: Bot, submission_id: int, user_id: int, username: str,
                                   collection_photos: list[str], receipt_files: list[str], db_instance: DB):
    admin_ids = await db_instance.get_all_admins()
    if MAIN_ADMIN_ID not in admin_ids:
        admin_ids.append(MAIN_ADMIN_ID)

    caption = (
        f"🚨 НОВАЯ ЗАЯВКА НА ПРОВЕРКУ! 🚨\n\n"
        f"<b>User ID:</b> {user_id}\n"
        f"<b>Username:</b> @{username}\n\n"
        f"Все фото, а также email, отправлены на почту."
    )
    keyboard = get_admin_keyboard(submission_id, user_id)
    all_files = collection_photos + receipt_files

    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, caption)

            photo_media_group = [InputMediaPhoto(media=photo_id) for photo_id in collection_photos]
            if photo_media_group:
                for i in range(0, len(photo_media_group), 10):
                    await bot.send_media_group(admin_id, media=photo_media_group[i:i + 10])

            for file_id in receipt_files:
                file_info = await bot.get_file(file_id)
                if file_info.file_path and file_info.file_path.endswith('.pdf'):
                    await bot.send_document(admin_id, document=file_id, caption="📄 Чек (PDF)")
                else:
                    await bot.send_photo(admin_id, photo=file_id, caption="📄 Чек (Фото)")

            await bot.send_message(admin_id, "Выберите действие:", reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Не удалось отправить заявку админу {admin_id}: {e}")

    await send_email_with_files(
        bot=bot,
        caption=f"Новая заявка №{submission_id} от @{username} (ID: {user_id})",
        file_ids=all_files
    )


# --- Обработка действий админа ---
@router.callback_query(F.data.startswith("admin:"), IsAdmin())
async def process_admin_action(callback: CallbackQuery, bot: Bot, db_instance: DB, state: FSMContext):
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
            await callback.message.edit_text(
                f"✅ Заявка №{submission_id} {status_text[action]}.",
                reply_markup=None
            )
        except Exception as e:
            logger.warning(f"Could not edit admin message for submission {submission_id}: {e}")
            await callback.message.answer(f"Заявка №{submission_id} {status_text[action]}.")


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

    await bot.edit_message_text(
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


# --- Команды управления админами ---
@router.message(Command("add_admin"), IsMainAdmin())
async def cmd_add_admin(message: Message, command: CommandObject, db_instance: DB):
    if not command.args or not command.args.isdigit():
        await message.answer("Пожалуйста, укажите ID пользователя. Пример: `/add_admin 12345678`")
        return

    admin_id_to_add = int(command.args)
    await db_instance.add_admin(admin_id_to_add)
    await message.answer(f"Администратор с ID `{admin_id_to_add}` успешно добавлен.")


@router.message(Command("remove_admin"), IsMainAdmin())
async def cmd_remove_admin(message: Message, command: CommandObject, db_instance: DB):
    if not command.args or not command.args.isdigit():
        await message.answer("Пожалуйста, укажите ID пользователя. Пример: `/remove_admin 12345678`")
        return

    admin_id_to_remove = int(command.args)
    if admin_id_to_remove == MAIN_ADMIN_ID:
        await message.answer("Нельзя удалить главного администратора.")
        return

    await db_instance.remove_admin(admin_id_to_remove)
    await message.answer(f"Администратор с ID `{admin_id_to_remove}` удален.")


@router.message(Command("list_admins"), IsMainAdmin())
async def cmd_list_admins(message: Message, db_instance: DB):
    admins = await db_instance.get_all_admins()

    text = f"<b>Главный администратор:</b>\n- `{MAIN_ADMIN_ID}`\n\n<b>Другие администраторы:</b>\n"
    other_admins = [f"- `{admin_id}`" for admin_id in admins if admin_id != MAIN_ADMIN_ID]
    if other_admins:
        text += "\n".join(other_admins)
    else:
        text += "Список пуст."

    await message.answer(text)


# --- Экспорт ---
@router.message(Command("get_users_db"), IsAdmin())
async def cmd_get_users_db(message: Message, bot: Bot, db_instance: DB):
    wait_message = await message.answer("Подготовка данных пользователей...")
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
    finally:
        await wait_message.delete()


# --- Рассылка напоминаний ---
async def send_reminder_job(bot: Bot, db_instance: DB):
    users = await db_instance.get_approved_users()
    text = "Напоминаем, что уже сегодня пройдет розыгрыш призов! 🏆 Следите за новостями в нашем тг канале ______"
    count = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
            await asyncio.sleep(0.1)
        except Exception:
            pass
    logger.info(f"Рассылка напоминаний завершена. Отправлено {count} сообщений.")


@router.message(Command("send_raffle_reminder"), IsAdmin())
async def cmd_send_raffle_reminder(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Когда отправить напоминание о розыгрыше?", reply_markup=get_schedule_keyboard())
    await state.set_state(AdminFSM.awaiting_reminder_schedule)


@router.callback_query(AdminFSM.awaiting_reminder_schedule, F.data == "send_now")
async def process_reminder_send_now(callback: CallbackQuery, bot: Bot, db_instance: DB, state: FSMContext):
    await callback.message.edit_text("Начинаю рассылку напоминаний...")
    await send_reminder_job(bot, db_instance)
    await callback.message.answer("Рассылка завершена.")
    await state.clear()


@router.callback_query(AdminFSM.awaiting_reminder_schedule, F.data == "send_schedule")
async def process_reminder_schedule(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Пожалуйста, введите дату и время для отправки в формате `ДД.ММ.ГГГГ ЧЧ:ММ` (например, `14.07.2025 15:30`).")


@router.message(AdminFSM.awaiting_reminder_schedule, F.text)
async def process_reminder_time(message: Message, state: FSMContext, scheduler: AsyncIOScheduler, bot: Bot,
                                db_instance: DB):
    try:
        scheduled_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        scheduler.add_job(send_reminder_job, 'date', run_date=scheduled_time, args=[bot, db_instance])
        await message.answer(f"Рассылка напоминаний запланирована на {scheduled_time.strftime('%d.%m.%Y в %H:%M')}.")
    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, используйте `ДД.ММ.ГГГГ ЧЧ:ММ`.")
    finally:
        await state.clear()


# --- Рассылка результатов ---
async def send_results_job(bot: Bot, db_instance: DB, results_link: str):
    users = await db_instance.get_approved_users()
    text = f"Розыгрыш завершен, результаты доступны по ссылке: {results_link}"
    count = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
            await asyncio.sleep(0.1)
        except Exception:
            pass
    logger.info(f"Рассылка результатов завершена. Отправлено {count} сообщений.")


@router.message(Command("send_results"), IsAdmin())
async def cmd_send_results(message: Message, state: FSMContext, command: CommandObject):
    if not command.args:
        await message.answer(
            "Пожалуйста, укажите ссылку на результаты после команды. \nПример: `/send_results https://t.me/your_channel/123`")
        return

    await state.clear()
    await state.update_data(results_link=command.args)
    await message.answer("Когда отправить результаты розыгрыша?", reply_markup=get_schedule_keyboard())
    await state.set_state(AdminFSM.awaiting_results_schedule)


@router.callback_query(AdminFSM.awaiting_results_schedule, F.data == "send_now")
async def process_results_send_now(callback: CallbackQuery, bot: Bot, db_instance: DB, state: FSMContext):
    data = await state.get_data()
    link = data.get("results_link")

    await callback.message.edit_text("Начинаю рассылку результатов...")
    await send_results_job(bot, db_instance, link)
    await callback.message.answer("Рассылка завершена.")
    await state.clear()


@router.callback_query(AdminFSM.awaiting_results_schedule, F.data == "send_schedule")
async def process_results_schedule(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Пожалуйста, введите дату и время для отправки в формате `ДД.ММ.ГГГГ ЧЧ:ММ` (например, `14.07.2025 15:30`).")


@router.message(AdminFSM.awaiting_results_schedule, F.text)
async def process_results_time(message: Message, state: FSMContext, scheduler: AsyncIOScheduler, bot: Bot,
                               db_instance: DB):
    data = await state.get_data()
    link = data.get("results_link")

    try:
        scheduled_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        scheduler.add_job(send_results_job, 'date', run_date=scheduled_time, args=[bot, db_instance, link])
        await message.answer(f"Рассылка результатов запланирована на {scheduled_time.strftime('%d.%m.%Y в %H:%M')}.")
    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, используйте `ДД.ММ.ГГГГ ЧЧ:ММ`.")
    finally:
        await state.clear()