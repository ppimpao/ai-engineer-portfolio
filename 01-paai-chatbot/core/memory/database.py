import aiosqlite
from typing import List, Dict
from core.config import settings

CREATE_CONVERSATIONS = """
CREATE TABLE IF NOT EXISTS conversations (
    chat_id   INTEGER PRIMARY KEY,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    role        TEXT    NOT NULL CHECK(role IN ('user', 'assistant')),
    content     TEXT    NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_id) REFERENCES conversations(chat_id)
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(CREATE_CONVERSATIONS)
        await db.execute(CREATE_MESSAGES)
        await db.commit()


async def ensure_conversation(chat_id: int) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO conversations (chat_id) VALUES (?)", (chat_id,)
        )
        await db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?",
            (chat_id,),
        )
        await db.commit()


async def save_message(chat_id: int, role: str, content: str, token_count: int) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT INTO messages (chat_id, role, content, token_count) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, token_count),
        )
        await db.commit()


async def get_messages(chat_id: int) -> List[Dict]:
    """Return all messages for a conversation, oldest first."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role, content, token_count FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
            (chat_id,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def delete_conversation(chat_id: int) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        await db.execute("DELETE FROM conversations WHERE chat_id = ?", (chat_id,))
        await db.commit()


async def get_message_count(chat_id: int) -> int:
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM messages WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0
