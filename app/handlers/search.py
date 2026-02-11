from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states import BotState
from app.services.storage import Storage
from app.keyboards.keyboards import search_next_keyboard, main_menu

router = Router()
storage = Storage()


@router.message(F.text == "🔍 Поиск")
async def start_search(message: Message, state: FSMContext):
    # 🔑 Меню — точка входа
    await state.clear()
    await state.set_state(BotState.SEARCH)
    await message.answer("Введите текст для поиска")


@router.message(BotState.SEARCH)
async def handle_search(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        return

    result = storage.search(query, offset=0)

    if not result:
        await state.clear()
        await message.answer(
            "Ничего не найдено",
            reply_markup=main_menu()
        )
        return

    await state.update_data(query=query, offset=0)

    await message.answer(
        result["text"],
        reply_markup=search_next_keyboard()
    )


@router.callback_query(F.data == "search_next", BotState.SEARCH)
async def search_next(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    query = data["query"]
    offset = data["offset"] + 1

    result = storage.search(query, offset)

    if not result:
        await state.clear()
        await callback.message.answer(
            "Это было последнее совпадение",
            reply_markup=main_menu()
        )
        return

    await state.update_data(offset=offset)

    await callback.message.answer(
        result["text"],
        reply_markup=search_next_keyboard()
    )
