from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List

from app.services.storage import get_connection


# =====================
# STATES
# =====================

class MemoryState(str, Enum):
    NEW = "NEW"
    LEARNING = "LEARNING"
    REMEMBERED = "REMEMBERED"
    FORGOTTEN = "FORGOTTEN"


# =====================
# MODEL
# =====================

@dataclass
class MemoryItem:
    id: int
    text: str

    state: MemoryState = MemoryState.NEW
    success_count: int = 0
    fail_count: int = 0

    last_attempt_at: Optional[datetime] = None
    next_due_at: Optional[datetime] = None

    favorite: bool = False
    created_at: datetime = datetime.utcnow()


# =====================
# DB → MEMORY (SRS)
# =====================

def load_due_items(limit: int = 20) -> List[MemoryItem]:
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                id, text, state,
                success_count, fail_count,
                last_attempt_at, next_due_at
            FROM quotes
            WHERE
                next_due_at IS NULL
                OR next_due_at <= ?
            ORDER BY next_due_at ASC
            LIMIT ?
            """,
            (now, limit)
        )
        rows = cur.fetchall()

    items: List[MemoryItem] = []

    for row in rows:
        (
            qid, text, state,
            success, fail,
            last_attempt, next_due
        ) = row

        items.append(
            MemoryItem(
                id=qid,
                text=text,
                state=MemoryState(state),
                success_count=success,
                fail_count=fail,
                last_attempt_at=datetime.fromisoformat(last_attempt) if last_attempt else None,
                next_due_at=datetime.fromisoformat(next_due) if next_due else None,
            )
        )

    return items


# =====================
# SCHEDULER
# =====================

def calc_next_due(state: MemoryState) -> datetime:
    now = datetime.utcnow()

    if state == MemoryState.NEW:
        return now + timedelta(hours=1)

    if state == MemoryState.LEARNING:
        return now + timedelta(hours=8)

    if state == MemoryState.FORGOTTEN:
        return now + timedelta(hours=2)

    if state == MemoryState.REMEMBERED:
        return now + timedelta(days=3)

    return now + timedelta(hours=12)


# =====================
# TRANSITIONS
# =====================

REMEMBER_THRESHOLD = 3


def answer_remember(item: MemoryItem) -> MemoryItem:
    now = datetime.utcnow()

    item.success_count += 1
    item.fail_count = 0
    item.last_attempt_at = now

    if item.state in (MemoryState.NEW, MemoryState.FORGOTTEN):
        item.state = MemoryState.LEARNING
    elif item.state == MemoryState.LEARNING:
        if item.success_count >= REMEMBER_THRESHOLD:
            item.state = MemoryState.REMEMBERED

    item.next_due_at = calc_next_due(item.state)
    return item


def answer_forget(item: MemoryItem) -> MemoryItem:
    now = datetime.utcnow()

    item.fail_count += 1
    item.success_count = 0
    item.last_attempt_at = now

    if item.state == MemoryState.REMEMBERED:
        item.state = MemoryState.FORGOTTEN
    elif item.state == MemoryState.NEW:
        item.state = MemoryState.LEARNING

    item.next_due_at = calc_next_due(item.state)
    return item


# =====================
# PICKER
# =====================

def pick_next(items: List[MemoryItem]) -> Optional[MemoryItem]:
    if not items:
        return None

    def priority(i: MemoryItem) -> int:
        score = 0
        if i.state == MemoryState.FORGOTTEN:
            score += 100
        elif i.state == MemoryState.NEW:
            score += 80
        elif i.state == MemoryState.LEARNING:
            score += 50
        else:
            score += 10

        score += i.fail_count * 5
        return score

    items.sort(key=priority, reverse=True)
    return items[0]
