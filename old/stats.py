from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.states import BotState
from app.services.storage import Storage
from app.keyboards.keyboards import main_menu

router = Router()
storage = Storage()


@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(BotState.STATS)

    stats = storage.get_stats_summary()

    text = (
        "📊 Статистика памяти\n\n"
        f"Всего цитат: {stats['total']}\n\n"
        f"❌ Забытые: {stats['forgotten']}\n"
        f"🟡 В изучении: {stats['learning']}\n"
        f"✅ Выученные: {stats['remembered']}\n\n"
        f"Попытки:\n"
        f"— Помнил: {stats['success']}\n"
        f"— Не помнил: {stats['fail']}"
    )

    await message.answer(text, reply_markup=main_menu())
