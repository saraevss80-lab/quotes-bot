import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.train import router as train_router
from app.handlers.search import router as search_router
from app.handlers.stats import router as stats_router
from app.handlers.idle import router as idle_router
from app.handlers.reminder import router as reminder_router

from app.services.scheduler import ReminderScheduler


BOT_TOKEN = "8305289390:AAGj5biHx1qyA45PxfFHsFTZryuGiSzFW0s"

# 🔴 ВАЖНО: твой chat_id
CHAT_ID = 103633786

async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(train_router)
    dp.include_router(search_router)
    dp.include_router(stats_router)
    dp.include_router(idle_router)
    dp.include_router(reminder_router)

    # 🔴 запускаем планировщик ОДИН РАЗ
    scheduler = ReminderScheduler(bot, chat_id=CHAT_ID)
    asyncio.create_task(scheduler.run_forever())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
