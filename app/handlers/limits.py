import re
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from app.handlers.states import LimitState


from app.utils.constants import PERIODS

import app.database.orm_query as qr
import app.keyboards.keyboard as kb

router = Router()

@router.message(LimitState.waiting_for_amount)
async def enter_limit(message: Message, state: FSMContext, session: AsyncSession):
    try:
        limit_amount = float(message.text.replace(',','.'))
    except ValueError:
        return await message.answer("❌ Введите корректное число")
    await state.update_data(limit_amount = limit_amount)
    await message.answer('Введите период на который вы хотите установить лимит')
    await state.set_state(LimitState.waiting_for_period)

@router.message(LimitState.waiting_for_period)
async def enter_limit_period(message: Message, state: FSMContext, session: AsyncSession):
    user_input = message.text.strip().lower()
    user = await qr.orm_get_user_by_tg_id(session, message.from_user.id)
    state_data = await state.get_data()

    if user_input in PERIODS:
        period = PERIODS[user_input]
    elif re.fullmatch(r"\d{1,3}d", user_input):
        period = user_input
    else:
        await message.answer(
            "❌ Неверный формат периода.\nВведите:\n• число с 'd' на конце (например, 30d)\n• или одно из слов: day, week, month, year"
        )
        return

    await state.update_data(period=period)

    await message.answer("🔁 Хотите ли вы, чтобы лимит автоматически обновлялся по завершении периода? (да/нет)")
    await state.set_state(LimitState.waiting_for_confirmation)

@router.message(LimitState.waiting_for_confirmation)
async def confirm_limit_updating(message: Message, session: AsyncSession, state: FSMContext):
    user_response = message.text.strip().lower()
    is_updating = None

    if user_response in ("да", "yes", "y"):
        is_updating = True
    elif user_response in ("нет", "no", "n"):
        is_updating = False
    else:
        await message.answer("❌ Введите 'да' или 'нет'")
        return

    state_data = await state.get_data()
    user = await qr.orm_get_user_by_tg_id(session, message.from_user.id)
    user_currency = await qr.orm_get_user_currency(session, user.id)

    data = {
        "user_id": user.id,
        "category_id": state_data["category_id"],
        "limit_amount": state_data["limit_amount"],
        "period": state_data["period"],
        "is_updating": is_updating,
        "currency_id": user_currency.id,
        "start_date": datetime.now(timezone.utc),
    }

    await qr.orm_set_category_limit(session, data)

    updating_text = "с автообновлением" if is_updating else "без автообновления"
    await message.answer(f"✅ Лимит установлен: {data['limit_amount']}{user_currency.symbol} на период: {data['period']} ({updating_text})")

    await state.clear()