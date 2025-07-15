# states.py

from aiogram.fsm.state import State, StatesGroup


class SubmissionFSM(StatesGroup):
    uploading_collection = State()
    uploading_receipts = State()
    confirmation = State()


class AdminFSM(StatesGroup):
    # Общие состояния
    reject_reason = State()
    awaiting_reminder_schedule = State()
    awaiting_results_schedule = State()

    # Состояния для управления админами
    awaiting_admin_to_add_id = State()
    awaiting_admin_to_remove_id = State()