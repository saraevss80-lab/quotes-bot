from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()


@router.message(Command("ping"))
async def ping_handler(message: Message):
    await message.answer("PONG")
