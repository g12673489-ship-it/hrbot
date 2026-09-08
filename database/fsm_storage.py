"""
Простое SQLite-хранилище для FSM состояний aiogram 3.x.
Позволяет FSM-состояниям переживать перезапуск бота.
"""
import json
import logging
import aiosqlite
from typing import Any, Dict, Optional

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType

logger = logging.getLogger(__name__)


class SqliteFSMStorage(BaseStorage):
    """
    FSM-хранилище на основе SQLite.
    Состояния и данные сохраняются на диск и переживают рестарты бота.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path

    async def init(self):
        """Создаёт таблицу если её ещё нет."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS fsm_data (
                    key TEXT PRIMARY KEY,
                    state TEXT,
                    data TEXT DEFAULT '{}'
                )
            """)
            await db.commit()
        logger.info(f"SqliteFSMStorage инициализирован: {self._db_path}")

    def _make_key(self, key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}"

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        db_key = self._make_key(key)
        state_str = state.state if isinstance(state, State) else state
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT INTO fsm_data (key, state) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET state = excluded.state
            """, (db_key, state_str))
            await db.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        db_key = self._make_key(key)
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT state FROM fsm_data WHERE key = ?", (db_key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        db_key = self._make_key(key)
        data_json = json.dumps(data, ensure_ascii=False)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT INTO fsm_data (key, data) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET data = excluded.data
            """, (db_key, data_json))
            await db.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        db_key = self._make_key(key)
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT data FROM fsm_data WHERE key = ?", (db_key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    try:
                        return json.loads(row[0])
                    except json.JSONDecodeError:
                        return {}
                return {}

    async def update_data(self, key: StorageKey, data: Dict[str, Any]) -> Dict[str, Any]:
        current = await self.get_data(key)
        current.update(data)
        await self.set_data(key, current)
        return current

    async def close(self) -> None:
        pass  # aiosqlite закрывает соединение сам через context manager
