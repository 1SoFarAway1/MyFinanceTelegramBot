from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.background.tasks import update_all_limits, delete_old_categories
from app.database.engine import session_maker 

async def scheduled_update_all_limits():
    async with session_maker() as session:
        await update_all_limits(session)

async def scheduled_delete_old_categories():
    async with session_maker() as session:
        await delete_old_categories(session)

def setup_scheduler():
    scheduler = AsyncIOScheduler()

    scheduler.add_job(scheduled_update_all_limits, CronTrigger(hour=0, minute=0))

    scheduler.add_job(scheduled_delete_old_categories, CronTrigger(hour=3, minute=0))

    scheduler.start()