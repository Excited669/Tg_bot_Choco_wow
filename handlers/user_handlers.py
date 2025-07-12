# handlers/user_handlers.py

import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.database import Database as DB
from handlers.admin_handlers import send_submission_to_admin  # Если эта функция импортируется

from keyboards.inline import get_start_keyboard, get_cancel_keyboard

router = Router()

logger = logging.getLogger(__name__)


# Определяем состояния для FSM
class SubmissionStates(StatesGroup):
    waiting_for_collection_photo = State()
    waiting_for_receipt_photo = State()
    waiting_for_full_name = State()  # Если эти состояния используются
    waiting_for_address = State()  # Если эти состояния используются
    waiting_for_phone_number = State()  # Если эти состояния используются


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()  # Сбрасываем все состояния при старте
    await message.answer(
        "Привет! 👋 Чтобы принять участие в розыгрыше призов от ChocoWow, "
        "тебе нужно сфотографировать свою коллекцию ChocoWow игрушек "
        "и чеки о покупке.\n\n"
        "Нажми 'Подать заявку' для начала:",
        reply_markup=get_start_keyboard()
    )


@router.callback_query(F.data == "submit_application")
async def start_submission(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Отвечаем на колбэк, чтобы убрать "часики"
    await callback.message.edit_text(
        "Отлично! Сначала отправь мне фото своей коллекции ChocoWow игрушек.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(SubmissionStates.waiting_for_collection_photo)


@router.message(SubmissionStates.waiting_for_collection_photo, F.photo)
async def process_collection_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id  # Берем фото наилучшего качества
    await state.update_data(collection_photo_id=photo_id)
    await message.answer(
        "Теперь отправь мне фото чеков, подтверждающих покупку ChocoWow.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(SubmissionStates.waiting_for_receipt_photo)


@router.message(SubmissionStates.waiting_for_collection_photo, ~F.photo)
async def process_collection_photo_invalid(message: Message):
    await message.answer("Пожалуйста, отправьте именно фотографию вашей коллекции.")


@router.message(SubmissionStates.waiting_for_receipt_photo, F.photo)
async def process_receipt_photo(message: Message, state: FSMContext, bot: Bot, db_instance: DB):
    receipt_photo_id = message.photo[-1].file_id
    user_data = await state.get_data()
    collection_photo_id = user_data.get("collection_photo_id")

    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else f"id_{user_id}"

    try:
        submission_id = await db_instance.add_submission(
            user_id, username, collection_photo_id, receipt_photo_id
        )
        await message.answer("Спасибо! Ваша заявка принята и будет рассмотрена администратором.")
        await state.clear()

        await send_submission_to_admin(
            bot=bot,
            submission_id=submission_id,
            user_id=user_id,
            username=username,
            collection_photo=collection_photo_id,
            receipt_photo=receipt_photo_id
        )

    except Exception as e:
        logger.error(f"Ошибка при добавлении заявки в БД для пользователя {user_id}: {e}")
        await message.answer("Произошла ошибка при обработке вашей заявки. Пожалуйста, попробуйте снова: /start")
        await state.clear()


@router.message(SubmissionStates.waiting_for_receipt_photo, ~F.photo)
async def process_receipt_photo_invalid(message: Message):
    await message.answer("Пожалуйста, отправьте именно фотографию чеков.")


@router.callback_query(F.data == "cancel_submission", F.state.in_(
    [SubmissionStates.waiting_for_collection_photo, SubmissionStates.waiting_for_receipt_photo]))
async def cancel_submission_process(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Подача заявки отменена.", show_alert=True)
    await state.clear()
    await callback.message.edit_text(
        "Подача заявки отменена. Вы можете начать заново, нажав 'Подать заявку'.",
        reply_markup=get_start_keyboard()
    )


# Обработка команды /cancel
@router.message(Command("cancel"), F.state.in_(
    [SubmissionStates.waiting_for_collection_photo, SubmissionStates.waiting_for_receipt_photo]))
async def cmd_cancel_submission(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Подача заявки отменена. Вы можете начать заново, нажав 'Подать заявку'.",
        reply_markup=get_start_keyboard()
    )