# keyboards/inline.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для начала подачи заявки."""
    buttons = [
        [InlineKeyboardButton(text="Подать заявку", callback_data="submit_application")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой отмены."""
    buttons = [
        [InlineKeyboardButton(text="Отменить", callback_data="cancel_submission")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard(submission_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Создает инлайн-клавиатуру для админа."""
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin:approve:{submission_id}:{user_id}")],
        [InlineKeyboardButton(text="🎁 С доп. призом", callback_data=f"admin:bonus:{submission_id}:{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:reject:{submission_id}:{user_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)