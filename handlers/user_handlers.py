# handlers/user_handlers.py

import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, ContentType, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from database.database import Database as DB
from keyboards.inline import get_start_keyboard, get_confirmation_keyboard, get_restart_keyboard
from keyboards.reply import get_done_keyboard
from states import SubmissionFSM

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db_instance: DB):
    await state.clear()
    user_exists = await db_instance.check_user_exists(message.from_user.id)
    if user_exists:
        await message.answer(
            "Вы уже отправляли свою заявку. Хотите перезаписать её и отправить данные заново?",
            reply_markup=get_restart_keyboard()
        )
    else:
        await message.answer(
            "Привет! 👋 Это бот для конкурса ChocoWow.\n\n"
            "Чтобы принять участие в розыгрыше призов, нажми кнопку ниже.",
            reply_markup=get_start_keyboard()
        )


@router.callback_query(F.data == "start_submission")
async def start_submission(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(
        "Отлично! Сначала отправь фото своей коллекции бегемотиков. Можно отправить несколько фото.\n\n"
        "Когда закончишь, нажми кнопку 'Готово'.",
        reply_markup=get_done_keyboard()
    )
    await state.set_state(SubmissionFSM.uploading_collection)
    await state.update_data(collection_photos=[])


@router.message(SubmissionFSM.uploading_collection, F.photo)
async def process_collection_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user_data = await state.get_data()
    user_data['collection_photos'].append(photo_id)
    await state.update_data(collection_photos=user_data['collection_photos'])

    sent_message = await message.answer("Фото добавлено. Можете отправить еще или нажать 'Готово'.")
    await asyncio.sleep(3)
    await sent_message.delete()


@router.message(SubmissionFSM.uploading_collection, F.text == "Готово")
async def finish_collection_upload(message: Message, state: FSMContext):
    user_data = await state.get_data()
    if not user_data.get('collection_photos'):
        await message.answer("Пожалуйста, отправьте хотя бы одно фото вашей коллекции.")
        return

    await message.answer(
        "Теперь вышлите фото или PDF-файлы чеков на Choco Wow.\n\n"
        "Когда закончишь, нажми кнопку 'Готово'.",
        reply_markup=get_done_keyboard()
    )
    await state.set_state(SubmissionFSM.uploading_receipts)
    await state.update_data(receipt_files=[])


@router.message(SubmissionFSM.uploading_receipts, F.content_type.in_({ContentType.PHOTO, ContentType.DOCUMENT}))
async def process_receipt_file(message: Message, state: FSMContext):
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and 'pdf' in message.document.mime_type:
        file_id = message.document.file_id
    else:
        await message.answer("Пожалуйста, отправьте фото или PDF файл.")
        return

    user_data = await state.get_data()
    user_data.get('receipt_files', []).append(file_id)
    await state.update_data(receipt_files=user_data.get('receipt_files'))

    sent_message = await message.answer("Файл добавлен. Можете отправить еще или нажать 'Готово'.")
    await asyncio.sleep(3)
    await sent_message.delete()


@router.message(SubmissionFSM.uploading_receipts, F.text == "Готово")
async def finish_receipts_upload(message: Message, state: FSMContext):
    user_data = await state.get_data()
    if not user_data.get('receipt_files'):
        await message.answer("Пожалуйста, отправьте хотя бы один файл (фото или PDF) с чеком.")
        return

    collection_count = len(user_data.get("collection_photos", []))
    receipt_count = len(user_data.get("receipt_files", []))

    wait_message = await message.answer("Пожалуйста, подождите...", reply_markup=ReplyKeyboardRemove())

    await message.answer(
        f"<b>Проверьте введенные данные:</b>\n\n"
        f"Фото коллекции: {collection_count} шт.\n"
        f"Файлы чеков: {receipt_count} шт.\n\n"
        f"<b>Все верно?</b>",
        reply_markup=get_confirmation_keyboard()
    )
    await wait_message.delete()
    await state.set_state(SubmissionFSM.confirmation)


@router.callback_query(SubmissionFSM.confirmation, F.data == "confirm_yes")
async def submission_confirmed(callback: CallbackQuery, state: FSMContext, bot: Bot, db_instance: DB):
    await callback.answer("Отправляем вашу заявку...")
    await callback.message.edit_text("Спасибо! Ваша заявка принята и будет рассмотрена администратором.")

    user_data = await state.get_data()
    user_id = callback.from_user.id
    username = callback.from_user.username if callback.from_user.username else f"id_{user_id}"

    try:
        submission_id = await db_instance.add_submission(
            user_id=user_id,
            username=username,
            collection_photos=user_data["collection_photos"],
            receipt_files=user_data["receipt_files"]
        )
        await bot.send_message(user_id,
                               "Ваша заявка успешно отправлена на проверку!\nМы уведомим вас о статусе заявки.")

        from handlers.admin_handlers import send_submission_to_admin

        await send_submission_to_admin(
            bot=bot,
            submission_id=submission_id,
            user_id=user_id,
            username=username,
            collection_photos=user_data["collection_photos"],
            receipt_files=user_data["receipt_files"],
            db_instance=db_instance
        )

    except Exception as e:
        logger.error(f"Ошибка при добавлении заявки в БД для пользователя {user_id}: {e}")
        await bot.send_message(user_id,
                               "Произошла ошибка при обработке вашей заявки. Пожалуйста, попробуйте снова: /start")
    finally:
        await state.clear()


@router.callback_query(SubmissionFSM.confirmation, F.data == "confirm_no")
async def submission_declined(callback: CallbackQuery, state: FSMContext, db_instance: DB):
    await callback.answer("Давайте начнем заново.", show_alert=True)
    await state.clear()
    await callback.message.delete()
    await cmd_start(callback.message, state, db_instance)