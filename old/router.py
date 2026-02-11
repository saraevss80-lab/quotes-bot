import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

from router import router

TOKEN = "8305289390:AAGj5biHx1qyA45PxfFHsFTZryuGiSzFW0s"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

dp.include_router(router)


@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("START OK")


# echo — ТОЛЬКО не-команды
@dp.message(F.text & ~F.text.startswith("/"))
async def echo_handler(message: Message):
    await message.answer(f"ECHO: {message.text}")


async def main():
    print(">>> BOT STARTING")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
