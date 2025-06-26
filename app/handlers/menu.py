from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.constants import INSTRUCTION_TEXTS

import app.keyboards.keyboard as kb

router = Router()

@router.message(F.text == '🗃️Категории')
async def get_category_menu(message: Message, session: AsyncSession):
    await message.answer("⚙️ Здесь вы можете настроить свои категории", reply_markup=await kb.category_menu())

@router.message(F.text == '📊Статистика')
async def get_category_menu(message: Message, session: AsyncSession):
    await message.answer("📊Здесь вы можете отслеживать свои доходы и расходы", reply_markup=await kb.statistics_menu())

@router.message(F.text == '🔙Назад')
async def get_category_menu(message: Message, session: AsyncSession):
    await message.answer("🔙Возвращаемся в главное меню", reply_markup=await kb.main_menu())

@router.callback_query(F.data == "to_main")
async def handle_to_main_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔙 Возврат в главное меню", reply_markup=await kb.main_menu())
    await callback.answer()

@router.message(F.text == '⚙️Настройки')
async def get_setting_menu(message: Message, session: AsyncSession):
    await message.answer('Меню настроек', reply_markup= await kb.settings_menu())

@router.message(F.text == '💱Выбрать валюту')
async def select_currency(message: Message, session: AsyncSession):
    await message.answer('Меню настроек', reply_markup= await kb.currencies(session))

@router.message(Command('instruction'))
async def get_instruction(message: Message, session: AsyncSession):
    for part in INSTRUCTION_TEXTS:
        await message.answer(part, parse_mode="HTML")