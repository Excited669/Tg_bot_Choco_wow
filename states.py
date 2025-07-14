# states.py

from aiogram.fsm.state import State, StatesGroup

class SubmissionFSM(StatesGroup):
    uploading_collection = State()
    uploading_receipts = State()
    confirmation = State()

class AdminFSM(StatesGroup):
    reject_reason = State()
    awaiting_reminder_schedule = State()
    awaiting_results_schedule = State()