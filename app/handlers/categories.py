from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Category
from app.handlers.states import CategoryState

import app.database.orm_query as qr
import app.keyboards.keyboard as kb

router = Router()

@router.message(F.text == '➕Добавить категорию')
async def add_category(message: Message, state: FSMContext, session: AsyncSession):
    user = await qr.orm_get_user_by_tg_id(session, message.from_user.id)
    if not user:
        return await message.answer("❌ Пользователь не найден. Пожалуйста, используйте команду /start.")
    
    await state.update_data(user_id=user.id)
    await message.answer("Введите название новой категории:")
    await state.set_state(CategoryState.waiting_for_name)

@router.message(F.text == '🗑️Удалить категорию')
async def delete_category(message: Message, state: FSMContext, session: AsyncSession):
    await message.answer('Выберите категорию, которую хотите удалить', reply_markup= 
                                                                await kb.categories(session, 'delete'))

@router.message(F.text == '♻️Восстановить категорию')
async def delete_category(message: Message, state: FSMContext, session: AsyncSession):
    await message.answer('Выберите категорию, которую хотите восстановить', reply_markup= 
                                                                await kb.deleted_categories(session, 'restore'))

@router.message(F.text == '✏️Редактировать категорию')
async def delete_category(message: Message, state: FSMContext, session: AsyncSession):
    await message.answer('Выберите категорию, которую хотите отредактировать', reply_markup= 
                                                                await kb.categories(session, 'update'))
    
@router.message(F.text == '📁Список категорий')
async def get_category_list(message: Message, state: FSMContext, session: AsyncSession):
    all_categories = await qr.orm_get_categories(session)
    active_categories = [category for category in all_categories if not category.is_deleted]

    if not active_categories:
        return "Нет активных категорий."

    categories_text = "\n".join([category.name for category in active_categories])
    await message.answer("Список всех ваших категорий")
    await message.answer(categories_text)


@router.message(CategoryState.waiting_for_name)
async def receive_category_name(message: Message, state: FSMContext, session: AsyncSession):
    state_data = await state.get_data()
    category_name = message.text.strip()

    if not category_name:
        return await message.answer("❌ Имя категории не может быть пустым. Попробуйте еще раз:")

    await qr.orm_add_category(session, user_id=state_data['user_id'], name=category_name)
    await message.answer(f"✅ Категория '{category_name}' была успешно добавлена!")
    await state.clear()

@router.message(CategoryState.waiting_for_update)
async def receive_category_update(message: Message, state: FSMContext, session: AsyncSession):
    state_data = await state.get_data()
    new_name = message.text.strip()

    if not new_name:
        return await message.answer("❌ Имя категории не может быть пустым. Попробуйте еще раз:")

    category_id = state_data.get("category_id")
    if not category_id:
        return await message.answer("❌ Произошла ошибка: не удалось найти выбранную категорию.")

    category = await session.get(Category, category_id)
    if not category:
        return await message.answer("Категория не найдена.")

    old_name = category.name
    await qr.orm_update_category(session, category_id, category_name=new_name)

    await message.answer(f"✅ Категория \"{old_name}\" успешно переименована в \"{new_name}\"!")
    await state.clear()

@router.message(F.text.lower().in_(["да", "нет"]), CategoryState.waiting_for_confirmation)
async def confirm_category_action(message: Message, state: FSMContext, session: AsyncSession):
    user_input = message.text.lower()
    data = await state.get_data()

    if user_input == "да":
        action = data["action"]
        category_id = data["category_id"]

        if action == "delete":
            await qr.orm_delete_category(session, category_id)
            await message.answer("✅ Категория удалена")
        elif action == "restore":
            await qr.orm_restore_category(session, category_id)
            await message.answer("✅ Категория восстановлена")
        else:
            await message.answer("❌ Неизвестное действие")
    else:
        await message.answer("❌ Действие отменено")

    await state.clear()