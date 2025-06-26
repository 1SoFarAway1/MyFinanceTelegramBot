from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from sqlalchemy import extract, func, select, update, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Limit, Transaction, User, Category, Setting, Currency
from app.database.query_helper import convert_transactions_to_currency
from app.utils.constants import DEFAULT_CATEGORIES, CURRENCIES

async def orm_add_default_categories(session: AsyncSession, user_id: int):
    
    for cat in DEFAULT_CATEGORIES:
        category = Category(
            user_id = user_id,
            name = cat["name"],
        )
        session.add(category)

async def orm_add_default_currencies(session: AsyncSession):
    for cur in CURRENCIES:
        result = await session.execute(
            select(Currency).where(Currency.code == cur["code"])
        )
        existing = result.scalar_one_or_none()

        if not existing:
            currency = Currency(
                code=cur["code"],
                name=cur["name"],
                symbol=cur["symbol"],
                rate_to_base = cur["rate_to_base"]
            )
            session.add(currency)

    await session.commit()

async def orm_add_default_settings(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Currency).where(Currency.code == "RUB")
    )
    rub_currency = result.scalar_one_or_none()
     
    default_setting = Setting(
        user_id=user_id,
        currency_id=rub_currency.id,
    )
    session.add(default_setting)

async def set_user(session: AsyncSession, tg_id: int, username: str):
    
    user = await session.scalar(
        select(User).where(User.tg_id == tg_id)
        )
    if not user:
        new_user = User(tg_id = tg_id, username = username)
        session.add(new_user)
        await session.flush()
        return new_user.id

async def orm_add_category(session: AsyncSession, name: str, user_id: int):
    new_category = Category(name = name, user_id = user_id)
    session.add(new_category)
    await session.commit()

async def orm_delete_category(session: AsyncSession, category_id: int):
    category = await session.get(Category, category_id)
    if category:
        category.is_deleted = True
        category.deleted_at = datetime.now(timezone.utc)
        await session.commit()

async def orm_restore_category(session: AsyncSession, category_id: int):
    category = await session.get(Category, category_id)
    if category:
        category.is_deleted = False
        category.deleted_at = None
        await session.commit()

async def orm_update_category(session: AsyncSession, category_id: int, category_name:str):
    category = await session.get(Category, category_id)
    if category:
        category.name = category_name
        await session.commit()

async def orm_get_categories(session: AsyncSession):
    return await session.scalars(select(Category))

async def orm_get_currencies(session: AsyncSession):
    return await session.scalars(select(Currency))

async def set_user_currency(session: AsyncSession, currency_id: int, user_id: int):

    await session.execute(
        update(Setting)
        .where(Setting.user_id == user_id)
        .values(currency_id=currency_id)
    )
    await session.commit()

async def orm_get_category_by_id(session: AsyncSession, category_id: int) -> Category:
    return await session.get(Category, category_id)

async def orm_get_currency_by_id(session: AsyncSession, currency_id: int) -> Currency:
    return await session.get(Currency, currency_id)

async def orm_get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User:
    stmt = select(User).where(User.tg_id == tg_id)
    return await session.scalar(stmt)

async def orm_make_transaction(session: AsyncSession, data: dict):

    new_transaction = Transaction(
        user_id = data["user_id"],
        category_id = data["category_id"],
        currency_id = data["currency_id"],
        amount = float(data["amount"]),
        is_expense = data["is_expense"],
        comment = data["comment"]
    )
    session.add(new_transaction)
    await session.commit()

async def orm_all_expenses(session: AsyncSession, user_id: int):
    user_currency_result = await session.execute(
        select(Setting.currency_id).where(Setting.user_id == user_id)
    )
    user_currency_id = user_currency_result.scalar()

    if user_currency_id is None:
        raise ValueError("Не установлена валюта пользователя")

    currencies_result = await session.execute(select(Currency))
    currencies = {c.id: c.rate_to_base for c in currencies_result.scalars()}
    user_rate = currencies.get(user_currency_id)

    if user_rate is None or user_rate == 0:
        raise ValueError("Нет курса для валюты пользователя")

    result = await session.execute(
        select(Category.name, Transaction.amount, Transaction.currency_id)
        .join(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.is_expense == True,
            Category.is_deleted == False
        )
    )

    totals_by_category = {}

    for category_name, amount, currency_id in result.all():
        tx_rate = currencies.get(currency_id)
        if tx_rate is None or tx_rate == 0:
            continue

        amount_in_user_currency = amount * (tx_rate / user_rate)

        totals_by_category[category_name] = totals_by_category.get(category_name, 0) + amount_in_user_currency

    return [(name, round(total, 2)) for name, total in totals_by_category.items()]

async def orm_all_income(session: AsyncSession, user_id: int):
    user_currency_result = await session.execute(
        select(Setting.currency_id).where(Setting.user_id == user_id)
    )
    user_currency_id = user_currency_result.scalar()

    if user_currency_id is None:
        raise ValueError("Не установлена валюта пользователя")

    currencies_result = await session.execute(select(Currency))
    currencies = {c.id: c.rate_to_base for c in currencies_result.scalars()}
    user_rate = currencies.get(user_currency_id)

    if user_rate is None or user_rate == 0:
        raise ValueError("Нет курса для валюты пользователя")

    result = await session.execute(
        select(Category.name, Transaction.amount, Transaction.currency_id)
        .join(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.is_expense == False,
            Category.is_deleted == False
        )
    )

    totals_by_category = {}

    for category_name, amount, currency_id in result.all():
        tx_rate = currencies.get(currency_id)
        if tx_rate is None or tx_rate == 0:
            continue

        amount_in_user_currency = amount * (tx_rate / user_rate)

        totals_by_category[category_name] = totals_by_category.get(category_name, 0) + amount_in_user_currency

    return [(name, round(total, 2)) for name, total in totals_by_category.items()]

async def orm_get_total_amount_by_category(session: AsyncSession, user_id: int, category_id: int):
    user_currency_result = await session.execute(
        select(Setting.currency_id).where(Setting.user_id == user_id)
    )
    user_currency_id = user_currency_result.scalar()

    currencies_result = await session.execute(select(Currency.id, Currency.rate_to_base))
    currencies = {row.id: row.rate_to_base for row in currencies_result.all()}

    user_currency_rate = currencies.get(user_currency_id)
    if user_currency_rate is None or user_currency_rate == 0:
        raise ValueError("Некорректный курс валюты пользователя")

    result = await session.execute(
        select(Transaction.amount, Transaction.currency_id)
        .where(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.is_expense == True
        )
    )
    transactions = result.all()

    totals_by_currency = {}
    total_in_user_currency = Decimal(0.0)

    for amount, currency_id in transactions:
        totals_by_currency[currency_id] = totals_by_currency.get(currency_id, Decimal(0.0)) + amount

        tx_rate = currencies.get(currency_id)
        if tx_rate and user_currency_rate:
            converted = amount * (tx_rate / user_currency_rate)
            total_in_user_currency += converted

    return total_in_user_currency, totals_by_currency

async def orm_get_last_transactions(session: AsyncSession, user_id: int, category_id: int, limit: int = 5):
    result = await session.execute(
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id
        )
        .order_by(desc(Transaction.created))
        .limit(limit)
    )
    return result.scalars().all()

async def orm_set_category_limit(session: AsyncSession, data: dict):
    await session.execute(
        delete(Limit).where(
            Limit.user_id == data["user_id"],
            Limit.category_id == data["category_id"]
        )
    )

    new_limit = Limit(
        user_id=data["user_id"],
        category_id=data["category_id"],
        limit_amount=float(data["limit_amount"]),
        period=data["period"],
        currency_id=data["currency_id"],
        start_date=data["start_date"],
        is_updating=data["is_updating"]
    )
    session.add(new_limit)

    await session.commit()

async def orm_get_category_limit(session: AsyncSession, user_id: int, category_id:int) -> Limit:
    result = await session.execute(
        select(Limit).where(
            Limit.category_id == category_id,
            Limit.user_id == user_id
            )
    )
    return result.scalar_one_or_none()

async def orm_get_monthly_expenses_by_category(session: AsyncSession, user_id: int):
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)

    user_currency_result = await session.execute(
        select(Setting.currency_id).where(Setting.user_id == user_id)
    )
    user_currency_id = user_currency_result.scalar()
    if user_currency_id is None:
        raise ValueError("Не установлена валюта пользователя")

    currencies_result = await session.execute(select(Currency))
    currencies = {c.id: c.rate_to_base for c in currencies_result.scalars()}
    user_rate = currencies.get(user_currency_id)
    if user_rate is None or user_rate == 0:
        raise ValueError("Нет курса для валюты пользователя")

    stmt = (
        select(Category.name, Transaction.amount, Transaction.currency_id)
        .join(Transaction.category)
        .where(
            Transaction.user_id == user_id,
            Transaction.is_expense == True,
            Transaction.created >= start_of_month,
            extract("month", Transaction.created) == now.month,
            Category.is_deleted == False
        )
    )

    result = await session.execute(stmt)

    totals_by_category = {}

    for category_name, amount, currency_id in result.all():
        tx_rate = currencies.get(currency_id)
        if tx_rate is None or tx_rate == 0:
            continue

        amount_in_user_currency = amount * (user_rate / tx_rate)
        totals_by_category[category_name] = totals_by_category.get(category_name, 0) + amount_in_user_currency

    return [(name, round(total, 2)) for name, total in totals_by_category.items()]

async def orm_get_monthly_income_by_category(session: AsyncSession, user_id: int):
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)

    user_currency_result = await session.execute(
        select(Setting.currency_id).where(Setting.user_id == user_id)
    )
    user_currency_id = user_currency_result.scalar()
    if user_currency_id is None:
        raise ValueError("Не установлена валюта пользователя")

    currencies_result = await session.execute(select(Currency))
    currencies = {c.id: c.rate_to_base for c in currencies_result.scalars()}
    user_rate = currencies.get(user_currency_id)
    if user_rate is None or user_rate == 0:
        raise ValueError("Нет курса для валюты пользователя")

    stmt = (
        select(Category.name, Transaction.amount, Transaction.currency_id)
        .join(Transaction.category)
        .where(
            Transaction.user_id == user_id,
            Transaction.is_expense == False,
            Transaction.created >= start_of_month,
            extract("month", Transaction.created) == now.month,
            Category.is_deleted == False
        )
    )

    result = await session.execute(stmt)

    totals_by_category = {}

    for category_name, amount, currency_id in result.all():
        tx_rate = currencies.get(currency_id)
        if tx_rate is None or tx_rate == 0:
            continue

        amount_in_user_currency = amount * (user_rate / tx_rate)
        totals_by_category[category_name] = totals_by_category.get(category_name, 0) + amount_in_user_currency

    return [(name, round(total, 2)) for name, total in totals_by_category.items()]

async def check_limit(session: AsyncSession, user_id: int, category_id: int) -> tuple[bool, float | None]:
    stmt_limit = select(Limit).where(
        Limit.user_id == user_id,
        Limit.category_id == category_id
    )
    result_limit = await session.execute(stmt_limit)
    limit = result_limit.scalar_one_or_none()

    if not limit or not limit.limit_amount or not limit.currency_id:
        return False, None

    start_date = limit.start_date
    if limit.period.endswith("d"):
        try:
            days = int(limit.period[:-1])
            end_date = start_date + timedelta(days=days)
        except ValueError:
            return False, None
    elif limit.period == "custom":
        end_date = limit.end_date
        if not end_date:
            return False, None
    else:
        return False, None

    stmt = select(Transaction.amount, Transaction.currency_id).where(
        Transaction.user_id == user_id,
        Transaction.category_id == category_id,
        Transaction.is_expense == True,
        Transaction.created >= start_date,
        Transaction.created <= end_date
    )
    result = await session.execute(stmt)
    transactions = result.all()

    if not transactions:
        return False, 0.0

    total_spent = await convert_transactions_to_currency(
        session=session,
        transactions=transactions,
        target_currency_id=limit.currency_id
    )

    percent_used = (total_spent / Decimal(limit.limit_amount)) * Decimal("100")
    exceeded = total_spent > Decimal(limit.limit_amount)

    return exceeded, float(percent_used)

async def orm_get_income_expense_by_months(session, user_id: int, months: int = 6):
    today = datetime.now()
    start_date = (today - timedelta(days=months * 30)).replace(day=1)
    end_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1)

    # Получаем валюту пользователя
    user_currency_result = await session.execute(
        select(Setting.currency_id).where(Setting.user_id == user_id)
    )
    user_currency_id = user_currency_result.scalar_one_or_none()

    if not user_currency_id:
        raise ValueError("Не установлена валюта пользователя")

    # Получаем курсы валют
    currencies_result = await session.execute(select(Currency.id, Currency.rate_to_base))
    currencies = {row.id: row.rate_to_base for row in currencies_result.all()}

    user_rate = currencies.get(user_currency_id)
    if not user_rate or user_rate == 0:
        raise ValueError("Нет курса для валюты пользователя")

    # Получаем данные по транзакциям
    stmt = (
        select(
            func.to_char(Transaction.created, 'YYYY-MM').label('month'),
            Transaction.is_expense,
            Category.name.label('category'),
            Transaction.amount,
            Transaction.currency_id
        )
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.created >= start_date,
            Transaction.created < end_date
        )
    )

    result = await session.execute(stmt)
    rows = result.all()

    # Агрегация с учётом валют
    summary = {}

    for month, is_expense, category, amount, currency_id in rows:
        tx_rate = currencies.get(currency_id)
        if not tx_rate or tx_rate == 0:
            continue

        # Конвертация в валюту пользователя
        converted_amount = Decimal(amount) * Decimal(user_rate) / Decimal(tx_rate)

        key = (month, is_expense, category)
        summary[key] = summary.get(key, Decimal(0)) + converted_amount

    # Возврат как список кортежей для совместимости
    return [
        (month, is_expense, category, round(total, 2))
        for (month, is_expense, category), total in sorted(summary.items())
    ]

async def orm_get_user_currency(session, user_id: int) -> Currency:
    result = await session.execute(
        select(Currency)
        .join(Setting, Setting.currency_id == Currency.id)
        .where(Setting.user_id == user_id)
    )
    return result.scalar_one_or_none()