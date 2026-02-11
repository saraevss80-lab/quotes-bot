from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.services.storage import Storage

router = Router()
storage = Storage()


@router.callback_query(F.data.startswith("reminder_remember:"))
async def reminder_remember(callback: CallbackQuery):
    await callback.answer()

    try:
        quote_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        return

    storage.mark_remember(quote_id)

    # убираем кнопки, текст не меняем
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("reminder_forget:"))
async def reminder_forget(callback: CallbackQuery):
    await callback.answer()

    try:
        quote_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        return

    storage.mark_forget(quote_id)

    row = storage.conn.execute(
        "SELECT text FROM quotes WHERE id = ?",
        (quote_id,),
    ).fetchone()

    if row:
        # показываем ПОЛНЫЙ ТЕКСТ и убираем кнопки
        await callback.message.edit_text(
            text=row["text"],
            reply_markup=None
        )
