from aiogram.fsm.state import StatesGroup, State

class TransactionState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_comment = State()

class CategoryState(StatesGroup):
    waiting_for_name = State()
    waiting_for_confirmation = State()
    waiting_for_update = State()

class LimitState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_period = State()
    waiting_for_confirmation = State()