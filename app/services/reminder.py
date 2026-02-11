from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.services.storage import Storage


class ReminderService:
    """
    Сервис напоминаний.
    Не знает про FSM.
    Не знает про handlers.
    Делает ОДНУ вещь: шлёт одно напоминание.
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.storage = Storage()

    def _build_keyboard(self, quote_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Помню",
                        callback_data=f"reminder_remember:{quote_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Не помню",
                        callback_data=f"reminder_forget:{quote_id}"
                    ),
                ]
            ]
        )

    def _make_fragment(self, text: str, success_count: int) -> str:
        """
        Адаптивный фрагмент для напоминаний:
        0      → первые 2 строки
        1–2    → чередуем
        >= 3   → последние 2 строки
        """
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

    async def send_one_reminder(self, chat_id: int) -> bool:
        quote = self.storage.get_quote_for_reminder()

        if not quote:
            return False

        fragment = self._make_fragment(
            quote["text"],
            quote["success_count"]
        )

        text = (
            "⏰ Напоминание\n\n"
            f"{fragment}"
        )

        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=self._build_keyboard(quote["id"])
        )

        return True
