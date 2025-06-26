from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

import app.database.orm_query as qr

router = Router()

@router.callback_query(F.data.startswith('currency_'))
async def handle_currency_action(callback: CallbackQuery, session: AsyncSession):
    user_tg_id = callback.from_user.id
    user = await qr.orm_get_user_by_tg_id(session, user_tg_id)

    if not user:
        return await callback.message.answer("❌ Пользователь не найден. Пожалуйста, используйте /start.")

    currency_id = int(callback.data.split("_")[1])
    currency = await qr.orm_get_currency_by_id(session, currency_id)

    if not currency:
        return await callback.message.answer("❌ Валюта не найдена.")

    await qr.set_user_currency(session, user_id=user.id, currency_id=currency_id)
    await callback.message.answer(f"✅ Ваша валюта изменена на {currency.name} ({currency.symbol})")
    await callback.answer()
