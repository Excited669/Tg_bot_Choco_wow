from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

def get_done_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой 'Готово'."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Готово")]],
        resize_keyboard=True,
        one_time_keyboard=False # Keep it until removed
    )

def get_remove_keyboard() -> ReplyKeyboardRemove:
    """Возвращает объект для удаления reply клавиатуры."""
    return ReplyKeyboardRemove()