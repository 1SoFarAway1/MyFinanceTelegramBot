from collections import defaultdict
import datetime
from decimal import Decimal
import io
from matplotlib.dates import relativedelta
import matplotlib.pyplot as plt

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Currency, Setting
import app.database.orm_query as qr

router = Router()

@router.message(F.text == '💸Все расходы')
async def all_expenses(message: Message, session: AsyncSession):
    user = await qr.orm_get_user_by_tg_id(session, message.from_user.id)
    expenses = await qr.orm_all_expenses(session, user.id)

    if not expenses:
        await message.answer("У вас пока нет трат.")
        return

    # Получаем валюту пользователя
    user_currency = await qr.orm_get_user_currency(session, user.id)
    currency_symbol = user_currency.symbol or user_currency.code

    text = f"Ваши траты по категориям в {currency_symbol}:\n\n"
    for name, total in expenses:
        # Приведение total к Decimal если не сделано заранее
        total = Decimal(total)
        text += f"• {name}: {total:.2f}{currency_symbol}\n"

    await message.answer(text)

@router.message(F.text == '💰Все доходы')
async def all_expenses(message: Message, session: AsyncSession):
    user = await qr.orm_get_user_by_tg_id(session, message.from_user.id)
    expenses = await qr.orm_all_income(session, user.id)

    if not expenses:
        await message.answer("У вас пока нет доходов.")
        return

    text = "Ваши доходы по категориям:\n\n"
    for name, total in expenses:
        text += f"• {name}: {total:.2f}\n"

    await message.answer(text)

@router.message(F.text == '📉Доля расходов')
async def expense_pie_chart(message: Message, session: AsyncSession):
    user = await qr.orm_get_user_by_tg_id(session, message.from_user.id)
    data = await qr.orm_get_monthly_expenses_by_category(session, user.id)
    await message.answer('Это может занять несколько секунд...')

    if not data:
        await message.answer("У вас нет трат за текущий месяц.")
        return

    labels, values = zip(*data)
    total = sum(values)

    filtered_labels = []
    filtered_values = []
    others_total = 0

    for label, value in zip(labels, values):
        percent = value / total
        if percent < 0.01:
            others_total += value
        else:
            filtered_labels.append(label)
            filtered_values.append(value)

    if others_total > 0:
        filtered_labels.append("Прочее")
        filtered_values.append(others_total)

    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        filtered_values,
        autopct=lambda pct: f'{pct:.1f}%' if pct >= 1 else '',
        startangle=90,
        pctdistance=0.7
    )

    for text in texts:
        text.set_text("")

    ax.legend(wedges, filtered_labels, title="Категории", loc="center left", bbox_to_anchor=(1, 0.5))
    ax.set_title("Расходы по категориям за текущий месяц", fontsize=12)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    photo = BufferedInputFile(buf.read(), filename="chart.png")
    await message.answer_photo(photo, caption="Диаграмма трат по категориям за текущий месяц")

@router.message(F.text == '📈Доля доходов')
async def income_pie_chart(message: Message, session: AsyncSession):
    user = await qr.orm_get_user_by_tg_id(session, message.from_user.id)
    data = await qr.orm_get_monthly_income_by_category(session, user.id)
    await message.answer('Это может занять несколько секунд...')

    if not data:
        await message.answer("У вас нет доходов за текущий месяц.")
        return

    labels, values = zip(*data)
    total = sum(values)

    filtered_labels = []
    filtered_values = []
    others_total = 0

    for label, value in zip(labels, values):
        percent = value / total
        if percent < 0.01:
            others_total += value
        else:
            filtered_labels.append(label)
            filtered_values.append(value)

    if others_total > 0:
        filtered_labels.append("Прочее")
        filtered_values.append(others_total)

    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        filtered_values,
        autopct=lambda pct: f'{pct:.1f}%' if pct >= 1 else '',
        startangle=90,
        pctdistance=0.7
    )

    for text in texts:
        text.set_text("")

    ax.legend(wedges, filtered_labels, title="Категории", loc="center left", bbox_to_anchor=(1, 0.5))
    ax.set_title("Доходы по категориям за текущий месяц", fontsize=12)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    photo = BufferedInputFile(buf.read(), filename="chart.png")
    await message.answer_photo(photo, caption="Диаграмма доходов по категориям за текущий месяц")

@router.message(F.text == '🗓️Полугодовой отчет')
async def six_months_comparison_chart(message: Message, session: AsyncSession):
    user = await qr.orm_get_user_by_tg_id(session, message.from_user.id)
    await message.answer("📊 Строим график, это может занять несколько секунд...")

    # Получаем агрегированные данные (приведённые к валюте пользователя)
    raw_data = await qr.orm_get_income_expense_by_months(session, user.id, months=6)

    if not raw_data:
        await message.answer("Нет данных о доходах и расходах за выбранный период.")
        return

    # Получаем символ валюты пользователя
    currency_result = await session.execute(
        select(Currency.symbol, Currency.code)
        .join(Setting, Setting.currency_id == Currency.id)
        .where(Setting.user_id == user.id)
    )
    currency_row = currency_result.first()
    currency_symbol = currency_row[0] or currency_row[1] or "₽"

    # Агрегируем данные
    summary = defaultdict(lambda: {"income": 0, "expense": 0})
    for month, is_expense, category, total in raw_data:
        type_key = "expense" if is_expense else "income"
        summary[month][type_key] += float(total)

    months = sorted(summary.keys())
    incomes = [summary[m]["income"] for m in months]
    expenses = [summary[m]["expense"] for m in months]

    # Построение графика
    x = range(len(months))
    bar_width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(
        [i - bar_width / 2 for i in x],
        expenses,
        width=bar_width,
        label="Расходы",
        color="salmon"
    )
    ax.bar(
        [i + bar_width / 2 for i in x],
        incomes,
        width=bar_width,
        label="Доходы",
        color="mediumseagreen"
    )

    ax.set_xticks(list(x))
    ax.set_xticklabels(months, rotation=45, ha='right')
    ax.set_ylabel(f"Сумма ({currency_symbol})")
    ax.set_title("Сравнение доходов и расходов за последние 6 месяцев")
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    # Отправка графика
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    photo = BufferedInputFile(buf.read(), filename="six_months_grouped_comparison_chart.png")
    await message.answer_photo(photo, caption="📊 Доходы и расходы за последние 6 месяцев")