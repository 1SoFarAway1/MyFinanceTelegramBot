from datetime import timedelta
from decimal import Decimal
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Currency, Setting
from app.handlers.states import LimitState, TransactionState, CategoryState

import app.database.orm_query as qr
import app.keyboards.keyboard as kb

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    existing_user = await qr.orm_get_user_by_tg_id(session, message.from_user.id)

    if existing_user:
        await message.answer(
            "👋 Вы уже зарегистрированы! Открываю главное меню.",
            reply_markup=await kb.main_menu()
        )
        return

    user_id = await qr.set_user(session, message.from_user.id, message.from_user.username)
    await qr.orm_add_default_currencies(session)
    await qr.orm_add_default_categories(session, user_id)
    await qr.orm_add_default_settings(session, user_id)
    await session.commit()

    await message.answer("✅ Вы были успешно зарегистрированы в боте!", reply_markup=await kb.main_menu())

@router.message(F.text == '📉Установить лимит')
async def get_categories(message: Message, session: AsyncSession):
    await message.answer('Выберите категорию на которую хотите установить лимит:', reply_markup= await kb.categories(session, 'setlimit'))

@router.message(F.text == '💸Записать трату/доход')
async def make_transaction(message: Message, session: AsyncSession):
    await message.answer('Выберите категорию из списка', reply_markup= await kb.categories(session, 'add'))

@router.message(F.text == '🧾История транзакций по категории')
async def view_category_expenses(message: Message, session: AsyncSession):
    await message.answer('Выберите категорию', reply_markup= await kb.categories(session, 'view'))
    
@router.callback_query(F.data.startswith('category_'))
async def handle_category_action(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
   action = callback.data.split("_")[1]
   category_id = int(callback.data.split("_")[2])
   category = await qr.orm_get_category_by_id(session, category_id)
   
   if action == "add":
    await state.update_data(category_id = category_id)
    await callback.message.answer('Введите сумму')
    await state.set_state(TransactionState.waiting_for_amount)

   elif action == "view":
    user = await qr.orm_get_user_by_tg_id(session, callback.from_user.id)
    limit = await qr.orm_get_category_limit(session, user.id, category_id)

    # Получаем валюту пользователя
    user_currency_id_result = await session.execute(
        select(Setting.currency_id).where(Setting.user_id == user.id)
    )
    user_currency_id = user_currency_id_result.scalar_one_or_none()

    # Получаем курсы валют
    currencies_result = await session.execute(select(Currency))
    currencies_list = list(currencies_result.scalars())
    currency_map = {
        currency.id: currency.symbol or currency.code
        for currency in currencies_list
    }
    currency_rates = {
        currency.id: currency.rate_to_base
        for currency in currencies_list
    }

    user_rate = currency_rates.get(user_currency_id)
    limit_rate = currency_rates.get(limit.currency_id) if limit else None

    # Получаем траты
    total, totals_by_currency = await qr.orm_get_total_amount_by_category(session, user.id, category_id)
    transactions = await qr.orm_get_last_transactions(session, user.id, category_id, limit=5)

    text = f"<b>Категория:</b> {category.name}\n"

    # Отображение лимита
    if limit and user_rate and limit_rate:
        total_in_limit_currency = total * (user_rate / limit_rate)
        percent_used = (Decimal(total_in_limit_currency) / limit.limit_amount * 100) if limit.limit_amount > 0 else 0
        limit_currency_symbol = currency_map.get(limit.currency_id, "₽")
        text += (
            f"<b>Установленный лимит:</b> {limit.limit_amount:.2f}{limit_currency_symbol}\n"
            f"<b>Израсходовано:</b> {total_in_limit_currency:.2f}{limit_currency_symbol} ({percent_used:.1f}%)\n"
        )
    else:
        text += "<b>Установленный лимит:</b> На данную категорию не установлен лимит\n"

    # Расходы по валютам
    if len(totals_by_currency) > 1:
        text += "<b>Расходы по валютам:</b>\n"
        for currency_id, amount in totals_by_currency.items():
            sym = currency_map.get(currency_id, "")
            text += f"  • {amount:.2f}{sym}\n"

    # Последние транзакции
    if transactions:
        text += "<b>Последние транзакции:</b>\n"
        for tx in transactions:
            icon = "🔻" if tx.is_expense else "🟢"
            local_time = tx.created + timedelta(hours=7)
            date = local_time.strftime('%d-%m-%Y %H:%M')
            comment = f" - {tx.comment}" if tx.comment else ""
            sign = "-" if tx.is_expense else "+"
            tx_currency_symbol = currency_map.get(tx.currency_id, "₽")
            text += f"{icon} {sign}{tx.amount:.2f}{tx_currency_symbol} ({date}){comment}\n"
    else:
        text += "Нет транзакций в этой категории."

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
   
   elif action == "setlimit":
       await state.update_data(category_id = category_id)
       await callback.message.answer('Введите сумму')
       await state.set_state(LimitState.waiting_for_amount)
    
   elif action == "delete":
       await state.update_data(category_id = category_id, action='delete')
       await callback.message.answer(f'❓ Вы точно хотите удалить категорию {category.name}?')
       await state.set_state(CategoryState.waiting_for_confirmation)
    
   elif action == "restore":
       await state.update_data(category_id = category_id, action = 'restore')
       await callback.message.answer(f'❓ Вы точно хотите восстановить категорию {category.name}?')
       await state.set_state(CategoryState.waiting_for_confirmation)

   elif action == "update":
       await state.update_data(category_id = category_id)
       await callback.message.answer(f'Введите новое имя {category.name}')
       await state.set_state(CategoryState.waiting_for_update)

@router.message(TransactionState.waiting_for_amount)
async def enter_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    is_expense = True
   
    if text.startswith('+'):
        is_expense = False
        text = text[1:]

    try:
        amount = float(text.replace(',', '.'))
    except ValueError:
        return await message.answer("❌ Введите правильный формат числа")

    await state.update_data(amount=amount, is_expense=is_expense)
    await message.answer("Введите комментарий. (Если комментарий не нужен, то введите '-'):")
    await state.set_state(TransactionState.waiting_for_comment)

@router.message(TransactionState.waiting_for_comment)
async def enter_comment(message: Message, state: FSMContext, session: AsyncSession):
    state_data = await state.get_data()
    comment = message.text if message.text != '-' else ''

    user = await qr.orm_get_user_by_tg_id(session, message.from_user.id)
    if not user:
        return await message.answer("Пользователь не найден. Пожалуйста, используйте команду /start.")
    
    user_currency = await qr.orm_get_user_currency(session, user.id)
    if not user_currency:
        return await message.answer("Не удалось получить настройки пользователя.")

    data = {
        "user_id": user.id,
        "category_id": state_data["category_id"],
        "amount": state_data["amount"],
        "is_expense": state_data["is_expense"],
        "comment": comment,
        "currency_id": user_currency.id 
    }

    await qr.orm_make_transaction(session, data)

    exceeded, percent = await qr.check_limit(session, user_id=user.id, category_id=state_data["category_id"])

    if exceeded:
        await message.answer(
            f"❗️ Вы превысили лимит по категории.\n"
            f"Использовано {percent:.1f}% от лимита."
        )
    elif percent is not None and percent >= 80:
        await message.answer(
            f"⚠️ Вы использовали {percent:.1f}% лимита по категории.\n"
            f"Осторожнее с расходами!"
        )

    await message.answer('Данные были успешно записаны')
    await state.clear()
