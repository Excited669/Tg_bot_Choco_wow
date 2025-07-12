from aiogram.fsm.state import State, StatesGroup

class UserPromo(StatesGroup):
    awaiting_collection_photo = State()
    awaiting_receipt_photo = State()

class AdminPromo(StatesGroup):
    awaiting_shipping_info = State() # Ожидание данных от пользователя