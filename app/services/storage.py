import sqlite3
import re
from datetime import datetime, timedelta
from typing import Optional, List
import random

DB_PATH = "data/quotes.db"


def normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ЖЁСТКАЯ СХЕМА ПОВТОРЕНИЙ (ДНИ)
REVIEW_INTERVALS = [3, 7, 14, 30]


class Storage:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_table()
        self._migrate()

    def _create_table(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                search_text TEXT NOT NULL,
                state TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                review_step INTEGER DEFAULT 0,
                next_review_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def _migrate(self):
        cur = self.conn.execute("PRAGMA table_info(quotes)")
        columns = {row["name"] for row in cur.fetchall()}

        if "review_step" not in columns:
            self.conn.execute(
                "ALTER TABLE quotes ADD COLUMN review_step INTEGER DEFAULT 0"
            )

        if "next_review_at" not in columns:
            self.conn.execute(
                "ALTER TABLE quotes ADD COLUMN next_review_at TEXT"
            )

        self.conn.commit()

    # ---------- SAVE ----------

    def save_quote(self, text: str) -> bool:
        search_text = normalize(text)

        cur = self.conn.execute(
            "SELECT 1 FROM quotes WHERE search_text = ?",
            (search_text,),
        )
        if cur.fetchone():
            return False

        now = datetime.utcnow()
        next_review = now + timedelta(days=REVIEW_INTERVALS[0])

        self.conn.execute(
            """
            INSERT INTO quotes (
                text,
                search_text,
                state,
                success_count,
                fail_count,
                review_step,
                next_review_at,
                created_at
            )
            VALUES (?, ?, 'NEW', 0, 0, 0, ?, ?)
            """,
            (
                text,
                search_text,
                next_review.isoformat(),
                now.isoformat(),
            ),
        )
        self.conn.commit()
        return True

    # ---------- TRAIN ----------

    def get_next_for_training(self) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(
            """
            SELECT *
            FROM quotes
            WHERE state IN ('FORGOTTEN', 'NEW', 'LEARNING')
            ORDER BY RANDOM()
            LIMIT 1
            """
        )
        return cur.fetchone()

    # ---------- SRS CORE ----------

    def mark_remember(self, quote_id: int):
        row = self.conn.execute(
            "SELECT review_step FROM quotes WHERE id = ?",
            (quote_id,),
        ).fetchone()

        if not row:
            return

        next_step = min(
            row["review_step"] + 1,
            len(REVIEW_INTERVALS) - 1
        )

        interval_days = REVIEW_INTERVALS[next_step]
        next_time = datetime.utcnow() + timedelta(days=interval_days)

        state = (
            "REMEMBERED"
            if next_step == len(REVIEW_INTERVALS) - 1
            else "LEARNING"
        )

        self.conn.execute(
            """
            UPDATE quotes
            SET
                success_count = success_count + 1,
                review_step = ?,
                next_review_at = ?,
                state = ?
            WHERE id = ?
            """,
            (
                next_step,
                next_time.isoformat(),
                state,
                quote_id,
            ),
        )
        self.conn.commit()

    def mark_forget(self, quote_id: int):
        # ❌ Немедленный возврат в ближайшее напоминание
        now = datetime.utcnow()

        self.conn.execute(
            """
            UPDATE quotes
            SET
                fail_count = fail_count + 1,
                success_count = 0,
                review_step = 0,
                next_review_at = ?,
                state = 'FORGOTTEN'
            WHERE id = ?
            """,
            (
                now.isoformat(),
                quote_id,
            ),
        )
        self.conn.commit()

    # ---------- REMINDER ENGINE ----------

    def get_quote_for_reminder(self) -> Optional[sqlite3.Row]:
        now = datetime.utcnow().isoformat()

        cur = self.conn.execute(
            """
            SELECT *
            FROM quotes
            WHERE
                state IN ('FORGOTTEN', 'NEW', 'LEARNING')
                AND next_review_at IS NOT NULL
                AND next_review_at <= ?
            """,
            (now,),
        )

        rows: List[sqlite3.Row] = cur.fetchall()
        if not rows:
            return None

        weighted_pool: List[sqlite3.Row] = []

        for row in rows:
            if row["state"] == "FORGOTTEN":
                weighted_pool.extend([row, row])
            else:
                weighted_pool.append(row)

        return random.choice(weighted_pool)

    # ---------- SEARCH ----------

    def search(self, query: str, offset: int):
        norm = normalize(query)
        words = norm.split()
        if not words:
            return None

        pattern = "%" + "%".join(words) + "%"

        cur = self.conn.execute(
            """
            SELECT *
            FROM quotes
            WHERE search_text LIKE ?
            ORDER BY created_at ASC
            LIMIT 1 OFFSET ?
            """,
            (pattern, offset),
        )
        return cur.fetchone()

    # ---------- STATS ----------

    def get_stats_summary(self) -> dict:
        total = self.conn.execute(
            "SELECT COUNT(*) FROM quotes"
        ).fetchone()[0]

        by_state = {
            row["state"]: row["cnt"]
            for row in self.conn.execute(
                """
                SELECT state, COUNT(*) as cnt
                FROM quotes
                GROUP BY state
                """
            ).fetchall()
        }

        totals = self.conn.execute(
            """
            SELECT
                SUM(success_count) as success,
                SUM(fail_count) as fail
            FROM quotes
            """
        ).fetchone()

        return {
            "total": total,
            "forgotten": by_state.get("FORGOTTEN", 0),
            "learning": by_state.get("LEARNING", 0),
            "remembered": by_state.get("REMEMBERED", 0),
            "success": totals["success"] or 0,
            "fail": totals["fail"] or 0,
        }
