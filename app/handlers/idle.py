from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.states import BotState
from app.services.storage import Storage
from app.keyboards.keyboards import main_menu

router = Router()
storage = Storage()

MENU_BUTTONS = {
    "🧠 Тренировка",
    "🔍 Поиск",
    "📊 Статистика",
}


@router.message(F.text)
async def idle_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()

    # принимаем текст только если не в режиме SEARCH
    if current_state == BotState.SEARCH:
        return

    text = message.text.strip()
    if not text:
        return

    if text in MENU_BUTTONS or text.startswith("/"):
        return

    saved = storage.save_quote(text)

    await message.answer(
        "Принято" if saved else "Уже есть",
        reply_markup=main_menu()
    )
