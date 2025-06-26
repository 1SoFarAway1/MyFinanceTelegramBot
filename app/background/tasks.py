from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Limit, Category

from dateutil.relativedelta import relativedelta

async def update_all_limits(session: AsyncSession):
    stmt = select(Limit).where(
        Limit.is_updating == True,
        Limit.start_date.isnot(None)
    )
    result = await session.execute(stmt)
    limits = result.scalars().all()

    now = datetime.now()

    for limit in limits:
        period = limit.period.lower()

        if not period.endswith('d'):
            continue 

        try:
            days = int(period[:-1])
        except ValueError:
            continue

        if not limit.end_date:
            limit.end_date = limit.start_date + timedelta(days=days)

        while limit.end_date < now:
            limit.start_date += timedelta(days=days)
            limit.end_date += timedelta(days=days)

    await session.commit()

async def delete_old_categories(session: AsyncSession):
    now = datetime.now(timezone.utc)
    threshold_date = now - timedelta(days=30)

    stmt = select(Category).where(
        Category.is_deleted == True,
        Category.deleted_at != None,
        Category.deleted_at < threshold_date
    )
    result = await session.execute(stmt)
    categories_to_delete = result.scalars().all()

    for category in categories_to_delete:
        await session.delete(category)

    await session.commit()