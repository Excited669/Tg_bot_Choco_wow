from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_start_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Участвовать в розыгрыше", callback_data="start_submission")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Отменить", callback_data="cancel_submission")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да, все верно", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Нет, заполнить заново", callback_data="confirm_no")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard(submission_id: int, user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:reject:{submission_id}:{user_id}"),
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin:approve:{submission_id}:{user_id}")
        ],
        [InlineKeyboardButton(text="🎁 С доп. призом", callback_data=f"admin:bonus:{submission_id}:{user_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_rejection_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Отклонить без причины", callback_data="reject_no_reason")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)