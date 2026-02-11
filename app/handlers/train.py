from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states import BotState
from app.services.storage import Storage
from app.keyboards.keyboards import train_keyboard, main_menu

router = Router()
storage = Storage()


def make_fragment(text: str, success_count: int) -> str:
    lines = [line for line in text.splitlines() if line.strip()]

    if len(lines) <= 2:
        return "\n".join(lines)

    if success_count == 0:
        return "\n".join(lines[:2]) + "\n…"

    if success_count in (1, 2):
        if success_count % 2 == 1:
            return "\n".join(lines[-2:]) + "\n…"
        else:
            return "\n".join(lines[:2]) + "\n…"

    return "\n".join(lines[-2:]) + "\n…"


async def show_next(message: Message, state: FSMContext):
    quote = storage.get_next_for_training()

    if not quote:
        await state.clear()
        await message.answer(
            "Тренировка завершена",
            reply_markup=main_menu()
        )
        return

    await state.set_state(BotState.TRAIN)
    await state.update_data(quote_id=quote["id"])

    fragment = make_fragment(
        quote["text"],
        quote["success_count"]
    )

    await message.answer(
        fragment,
        reply_markup=train_keyboard()
    )


@router.message(F.text == "🧠 Тренировка")
async def start_training(message: Message, state: FSMContext):
    # 🔑 Меню — точка входа
    await state.clear()
    await show_next(message, state)


@router.callback_query(F.data == "train_remember", BotState.TRAIN)
async def remember(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    quote_id = data.get("quote_id")
    if not quote_id:
        return

    storage.mark_remember(quote_id)
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data == "train_forget", BotState.TRAIN)
async def forget(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    quote_id = data.get("quote_id")
    if not quote_id:
        return

    storage.mark_forget(quote_id)

    row = storage.conn.execute(
        "SELECT text FROM quotes WHERE id = ?",
        (quote_id,),
    ).fetchone()

    if row:
        await callback.message.edit_text(row["text"])
