from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.orm_query import orm_get_categories, orm_get_currencies

async def categories(session: AsyncSession, action: str):
    all_categories = await orm_get_categories(session)
    
    active_categories = [category for category in all_categories if not category.is_deleted]

    keyboard = InlineKeyboardBuilder()
    for category in active_categories:
        keyboard.add(
            InlineKeyboardButton(
                text=category.name,
                callback_data=f"category_{action}_{category.id}"
            )
        )
    keyboard.add(InlineKeyboardButton(text="Cancel", callback_data="to_main"))
    return keyboard.adjust(1).as_markup()

async def currencies(session: AsyncSession):
    all_currencies = await orm_get_currencies(session)
    
    keyboard = InlineKeyboardBuilder()
    for currency in all_currencies:
        keyboard.add(
            InlineKeyboardButton(
                text=currency.code,
                callback_data=f"currency_{currency.id}"
            )
        )
    keyboard.add(InlineKeyboardButton(text="Cancel", callback_data="to_main"))
    return keyboard.adjust(1).as_markup()

async def deleted_categories(session: AsyncSession, action: str):
    all_categories = await orm_get_categories(session)
    
    active_categories = [category for category in all_categories if category.is_deleted]

    keyboard = InlineKeyboardBuilder()
    for category in active_categories:
        keyboard.add(
            InlineKeyboardButton(
                text=category.name,
                callback_data=f"category_{action}_{category.id}"
            )
        )
    keyboard.add(InlineKeyboardButton(text="Cancel", callback_data="to_main"))
    return keyboard.adjust(1).as_markup()

async def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💸Записать трату/доход"), KeyboardButton(text="📉Установить лимит")],
            [KeyboardButton(text="📊Статистика")],
            [KeyboardButton(text="🗃️Категории"), KeyboardButton(text="⚙️Настройки")]
        ],
        resize_keyboard=True,
        input_field_placeholder = 'Выберите действие',
        one_time_keyboard=False
    )

async def category_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕Добавить категорию")],
            [KeyboardButton(text="🗑️Удалить категорию"), KeyboardButton(text="♻️Восстановить категорию")],
            [KeyboardButton(text="✏️Редактировать категорию"), KeyboardButton(text="📁Список категорий")],
            [KeyboardButton(text="🔙Назад")]
        ],
        resize_keyboard=True,
        input_field_placeholder = 'Выберите действие'
    )

async def statistics_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💸Все расходы"), KeyboardButton(text="💰Все доходы")],
            [KeyboardButton(text="📉Доля расходов"), KeyboardButton(text="📈Доля доходов")],
            [KeyboardButton(text="🧾История транзакций по категории")],
            [KeyboardButton(text="🗓️Полугодовой отчет")],
            [KeyboardButton(text="🔙Назад")]
        ],
        resize_keyboard=True,
        input_field_placeholder = 'Выберите действие'
    )

async def settings_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💱Выбрать валюту"), KeyboardButton(text="🔙Назад")],
        ],
        resize_keyboard=True,
        input_field_placeholder = 'Выберите действие'
    )