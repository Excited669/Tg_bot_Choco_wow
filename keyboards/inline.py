# keyboards/inline.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


# --- Пользовательские клавиатуры ---

def get_start_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Участвовать в розыгрыше", callback_data="start_submission")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_restart_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Да, перезаписать заявку", callback_data="start_submission")]
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


# --- Админские клавиатуры ---

def get_admin_panel_keyboard(is_main_admin: bool) -> InlineKeyboardMarkup:
    """Главная панель администратора."""
    buttons = [
        [InlineKeyboardButton(text="📊 Выгрузить базу (CSV)", callback_data="admin_panel:get_db")],
        [
            InlineKeyboardButton(text="🔔 Напоминание", callback_data="admin_panel:send_reminder"),
            InlineKeyboardButton(text="🏆 Результаты", callback_data="admin_panel:send_results")
        ]
    ]
    if is_main_admin:
        buttons.append(
            [InlineKeyboardButton(text="👑 Управление администраторами", callback_data="admin_panel:manage_admins")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_management_keyboard() -> InlineKeyboardMarkup:
    """Панель управления администраторами."""
    buttons = [
        [
            InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_manage:add"),
            InlineKeyboardButton(text="➖ Удалить админа", callback_data="admin_manage:remove")
        ],
        [InlineKeyboardButton(text="👥 Список админов", callback_data="admin_manage:list")],
        [InlineKeyboardButton(text="⬅️ Назад в админ-панель", callback_data="admin_manage:back_to_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_remove_admin_keyboard(admins_with_names: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком админов для удаления."""
    buttons = []
    # Создаем кнопку для каждого админа
    for user_id, name in admins_with_names:
        buttons.append([InlineKeyboardButton(text=f"❌ {name}", callback_data=f"admin_remove_user:{user_id}")])

    # Добавляем кнопку "Назад"
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_manage:back_to_management")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard(submission_id: int, user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin:approve:{submission_id}:{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:reject:{submission_id}:{user_id}")
        ],
        [InlineKeyboardButton(text="🎁 С доп. призом", callback_data=f"admin:bonus:{submission_id}:{user_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_rejection_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Отклонить без причины", callback_data="reject_no_reason")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_schedule_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Отправить сейчас", callback_data="send_now"),
            InlineKeyboardButton(text="Запланировать", callback_data="send_schedule")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)