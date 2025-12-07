import logging
import sqlite3
import re
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==== НАСТРОЙКИ ====================================================

BOT_TOKEN = "8305289390:AAEW2tLSuqoTnFtXzsYyvcvciySWE9Y80MM"  # <-- сюда токен от BotFather
DB_PATH = "quotes.db"

# ==== ЛОГИРОВАНИЕ ==================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ==== РАБОТА С БД ==================================================

def init_db() -> None:
    """Создаём таблицу, если её ещё нет."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT UNIQUE,
            created_at TEXT,
            source_chat_id INTEGER,
            source_message_id INTEGER
        );
        """
    )
    conn.commit()
    conn.close()


def normalize_text(text: str) -> str:
    """
    Нормализуем текст для сравнения:
    - режем пробелы по краям
    - схлопываем подряд идущие пробелы/переносы.
    """
    # заменяем любое количество пробельных символов одним пробелом
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def add_or_get_record(
    text: str,
    source_chat_id: int | None,
    source_message_id: int | None,
) -> tuple[int, bool]:
    """
    Добавить запись, если её ещё нет.
    Возвращает (id, is_new):
      - id: номер записи в базе
      - is_new: True, если только что добавили, False если уже была
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    norm_text = normalize_text(text)

    # смотрим, есть ли уже такая запись
    cur.execute("SELECT id FROM records WHERE text = ?", (norm_text,))
    row = cur.fetchone()
    if row:
        record_id = row[0]
        conn.close()
        return record_id, False

    # если нет — вставляем новую
    created_at = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO records (text, created_at, source_chat_id, source_message_id)
        VALUES (?, ?, ?, ?)
        """,
        (norm_text, created_at, source_chat_id, source_message_id),
    )
    conn.commit()
    record_id = cur.lastrowid
    conn.close()
    return record_id, True


def get_record_by_id(record_id: int) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT text FROM records WHERE id = ?", (record_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


def get_stats() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM records")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


# ==== ХЕНДЛЕРЫ КОМАНД ==============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start — лёгкий онбординг.
    """
    text = (
        "Привет. Я бот-хранилище цитат и стихов.\n\n"
        "Просто пересылай мне сообщения (в том числе форварды) —\n"
        "я дам им порядковый номер и буду отсекать дубли.\n\n"
        "Команды:\n"
        "/stats – сколько записей в базе\n"
        "/get <id> – показать запись по номеру (например: /get 12)"
    )
    await update.message.reply_text(text)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /stats — количество записей.
    """
    count = get_stats()
    await update.message.reply_text(f"В базе сейчас {count} записей.")


async def get_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /get <id> — достать конкретную запись.
    """
    if not context.args:
        await update.message.reply_text("Укажи номер записи, например: /get 5")
        return

    try:
        record_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Номер должен быть целым числом, например: /get 5")
        return

    record = get_record_by_id(record_id)
    if not record:
        await update.message.reply_text(f"Запись с номером {record_id} не найдена.")
        return

    await update.message.reply_text(f"№{record_id}:\n{record}")


# ==== ХЕНДЛЕР ТЕКСТА / ФОРВАРДОВ ===================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатываем любые текстовые сообщения и форварды.
    Если текста нет (стикеры, фото без подписи) — просто выходим.
    """
    message = update.message
    if not message:
        return

    # вытаскиваем либо text, либо caption (если это сообщение с подписью)
    raw_text = message.text or message.caption
    if not raw_text:
        return

    source_chat_id = message.forward_from_chat.id if message.forward_from_chat else message.chat_id
    source_message_id = message.forward_from_message_id if message.forward_from_message_id else message.message_id

    record_id, is_new = add_or_get_record(
        text=raw_text,
        source_chat_id=source_chat_id,
        source_message_id=source_message_id,
    )

    if is_new:
        reply = f"Зафиксировал. Запись №{record_id}."
    else:
        reply = f"Такой текст уже есть в базе под №{record_id}. Дубликат не добавляю."

    await message.reply_text(reply)


# ==== ТОЧКА ВХОДА ==================================================

def main() -> None:
    # инициализация БД
    init_db()

    # сборка приложения
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("get", get_cmd))

    # все НЕ-командные сообщения — в хендлер
    app.add_handler(
        MessageHandler(
            filters.ALL & (~filters.COMMAND),
            handle_message,
        )
    )

    # запуск по long polling
    logger.info("Бот запущен. Ждём сообщений...")
    app.run_polling()


if __name__ == "__main__":
    main()
