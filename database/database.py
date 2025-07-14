# database/database.py

import aiosqlite
import json
from config import DB_NAME

class Database:
    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name
        self.conn = None

    async def connect(self):
        if self.conn is None:
            self.conn = await aiosqlite.connect(self.db_name)
            await self.conn.execute("PRAGMA foreign_keys = ON")

    async def close(self):
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        await self.connect()
        cursor = await self.conn.execute(query, params)
        await self.conn.commit()
        return cursor

    async def fetchone(self, query: str, params: tuple = ()):
        await self.connect()
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple = ()):
        await self.connect()
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def setup_database(self):
        await self.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                collection_photo_ids TEXT,
                receipt_file_ids TEXT,
                status TEXT DEFAULT 'pending'
            )
        ''')
        await self.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        print(f"Таблицы 'participants' и 'admins' проверены/созданы в {self.db_name}.")

    async def check_user_exists(self, user_id: int) -> bool:
        """Проверяет, существует ли участник в базе данных."""
        result = await self.fetchone('SELECT 1 FROM participants WHERE user_id = ?', (user_id,))
        return result is not None

    async def add_submission(self, user_id: int, username: str, collection_photos: list[str],
                             receipt_files: list[str]) -> int | None:
        collection_photos_json = json.dumps(collection_photos)
        receipt_files_json = json.dumps(receipt_files)

        await self.execute('''
            INSERT INTO participants (user_id, username, collection_photo_ids, receipt_file_ids, status)
            VALUES (?, ?, ?, ?, 'pending')
            ON CONFLICT(user_id) DO UPDATE SET
            collection_photo_ids = excluded.collection_photo_ids,
            receipt_file_ids = excluded.receipt_file_ids,
            status = 'pending',
            username = excluded.username
        ''', (user_id, username, collection_photos_json, receipt_files_json))

        row = await self.fetchone('SELECT id FROM participants WHERE user_id = ?', (user_id,))
        return row[0] if row else None

    async def update_status(self, user_id: int, status: str):
        await self.execute('UPDATE participants SET status = ? WHERE user_id = ?', (status, user_id))

    async def get_approved_users(self) -> list[int]:
        rows = await self.fetchall("SELECT user_id FROM participants WHERE status IN ('approved', 'bonus')")
        return [row[0] for row in rows]

    async def get_all_participants_data(self) -> tuple[list[str], list[tuple]]:
        await self.connect()
        query = "SELECT id, user_id, username, collection_photo_ids, receipt_file_ids, status FROM participants"
        async with self.conn.execute(query) as cursor:
            rows = await cursor.fetchall()
            column_names = [description[0] for description in cursor.description]
            return column_names, rows

    async def add_admin(self, user_id: int):
        await self.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))

    async def remove_admin(self, user_id: int):
        await self.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))

    async def get_all_admins(self) -> list[int]:
        rows = await self.fetchall('SELECT user_id FROM admins')
        return [row[0] for row in rows]