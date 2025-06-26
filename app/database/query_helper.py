from decimal import Decimal
from sqlalchemy import select
from app.database.models import Currency
from sqlalchemy.ext.asyncio import AsyncSession

async def convert_transactions_to_currency(
    session: AsyncSession,
    transactions: list[tuple[Decimal, int]],
    target_currency_id: int
) -> Decimal:

    result = await session.execute(select(Currency))
    currencies = result.scalars().all()

    currency_rates = {
        currency.id: Decimal(currency.rate_to_base) for currency in currencies
    }

    target_rate = currency_rates.get(target_currency_id)
    if target_rate is None or target_rate == 0:
        raise ValueError("Целевая валюта не найдена или некорректна")

    total_converted = Decimal("0")

    for amount, currency_id in transactions:
        original_rate = currency_rates.get(currency_id)
        if original_rate is None or original_rate == 0:
            continue  

        converted_amount = (Decimal(amount) * original_rate) / target_rate
        total_converted += converted_amount

    return total_converted.quantize(Decimal("0.01"))  