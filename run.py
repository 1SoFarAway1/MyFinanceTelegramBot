import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from app.background.scheduler import setup_scheduler

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())

from app.middlewares.db import DataBaseSession

from app.database.engine import create_db, drop_db, session_maker

import app.handlers.categories as categories 
import app.handlers.transactions as transactions
import app.handlers.statistics as statistics
import app.handlers.limits as limits
import app.handlers.menu as menu
import app.handlers.currencies as currencies

bot = Bot(token = os.getenv('TOKEN'))
dp = Dispatcher()

async def main():
    setup_scheduler()
    await create_db()
    #await drop_db()
    dp.update.middleware(DataBaseSession(session_pool = session_maker))

    dp.include_router(categories.router)
    dp.include_router(transactions.router)
    dp.include_router(statistics.router)
    dp.include_router(limits.router)
    dp.include_router(menu.router)
    dp.include_router(currencies.router)

    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
