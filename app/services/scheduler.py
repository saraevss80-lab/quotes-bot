import asyncio
import logging
from datetime import datetime, time, timedelta

from aiogram import Bot

from app.services.reminder import ReminderService


REMINDER_TIMES = [
    time(9, 0),   # утро
    time(14, 0),  # день
    time(20, 0),  # вечер
]


class ReminderScheduler:
    """
    Локальный планировщик напоминаний.
    Без FSM. Без хендлеров.
    Работает в фоне и НЕ влияет на polling.
    """

    def __init__(self, bot: Bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.reminder_service = ReminderService(bot)

        # ключ последнего успешно отправленного окна
        self._last_sent_key: str | None = None

    def _next_run(self) -> datetime:
        now = datetime.now()

        for t in REMINDER_TIMES:
            candidate = datetime.combine(now.date(), t)
            if candidate > now:
                return candidate

        # если все окна сегодня прошли — первое завтра
        return datetime.combine(
            now.date() + timedelta(days=1),
            REMINDER_TIMES[0],
        )

    def _window_key(self, dt: datetime) -> str:
        """
        Ключ окна, например: 2026-02-06-09:00
        """
        return dt.strftime("%Y-%m-%d-%H:%M")

    async def run_forever(self):
        logging.info("ReminderScheduler started")

        while True:
            try:
                next_run = self._next_run()
                sleep_seconds = (next_run - datetime.now()).total_seconds()

                if sleep_seconds > 0:
                    await asyncio.sleep(sleep_seconds)

                now = datetime.now()
                key = self._window_key(
                    datetime.combine(now.date(), next_run.time())
                )

                # защита от повторной отправки в то же окно
                if key != self._last_sent_key:
                    sent = await self.reminder_service.send_one_reminder(
                        chat_id=self.chat_id
                    )
                    if sent:
                        self._last_sent_key = key

                # пауза, чтобы не зациклиться на одной минуте
                await asyncio.sleep(60)

            except Exception as e:
                # НИКОГДА не даём планировщику умереть молча
                logging.exception(
                    "Error in ReminderScheduler, retrying in 60s"
                )
                await asyncio.sleep(60)
