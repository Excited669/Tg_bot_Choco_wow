# database/database.py

import aiosqlite
from config import DB_NAME  # Предполагается, что DB_NAME определен в config.py


class Database:
    """
    Класс для управления операциями с базой данных SQLite.
    Использует одно асинхронное соединение для всех операций.
    """

    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name
        self.conn = None  # Соединение с базой данных

    async def connect(self):
        """Устанавливает соединение с базой данных, если оно еще не установлено."""
        if self.conn is None:
            self.conn = await aiosqlite.connect(self.db_name)
            await self.conn.execute("PRAGMA foreign_keys = ON")  # Включаем поддержку внешних ключей

    async def close(self):
        """Закрывает соединение с базой данных."""
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        """
        Выполняет SQL-запрос и фиксирует изменения (COMMIT).
        Возвращает объект курсора.
        """
        await self.connect()  # Убедимся, что соединение активно
        async with self.conn.execute(query, params) as cursor:
            await self.conn.commit()
            return cursor

    async def fetchone(self, query: str, params: tuple = ()):
        """
        Выполняет SQL-запрос и возвращает одну строку результата (кортеж).
        """
        await self.connect()
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple = ()):
        """
        Выполняет SQL-запрос и возвращает все строки результата (список кортежей).
        """
        await self.connect()
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def setup_database(self):
        """
        Создает таблицы в базе данных, если они еще не существуют.
        Вызывается при запуске приложения.
        """
        await self.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                collection_photo_id TEXT,
                receipt_photo_id TEXT,
                status TEXT DEFAULT 'pending',
                full_name TEXT,
                address TEXT,
                phone_number TEXT
            )
        ''')
        print(f"Таблица 'participants' проверена/создана в {self.db_name}.")

    async def add_submission(self, user_id: int, username: str, collection_photo: str,
                             receipt_photo: str) -> int | None:
        """
        Добавляет новую заявку участника или обновляет существующую.
        Возвращает ID записи.
        """
        await self.execute('''
            INSERT INTO participants (user_id, username, collection_photo_id, receipt_photo_id, status)
            VALUES (?, ?, ?, ?, 'pending')
            ON CONFLICT(user_id) DO UPDATE SET
            collection_photo_id = excluded.collection_photo_id,
            receipt_photo_id = excluded.receipt_photo_id,
            status = 'pending'
        ''', (user_id, username, collection_photo, receipt_photo))

        row = await self.fetchone('SELECT id FROM participants WHERE user_id = ?', (user_id,))
        return row[0] if row else None

    async def update_status(self, user_id: int, status: str):
        """Обновляет статус участника."""
        await self.execute('UPDATE participants SET status = ? WHERE user_id = ?', (status, user_id))

    async def get_approved_users(self) -> list[int]:
        """Возвращает user_id всех подтвержденных участников."""
        rows = await self.fetchall("SELECT user_id FROM participants WHERE status IN ('approved', 'bonus')")
        return [row[0] for row in rows]

    async def get_all_participants_data(self) -> tuple[list[str], list[tuple]]:
        """
        Возвращает данные из таблицы 'participants' для экспорта в CSV,
        исключая 'full_name', 'address', 'phone_number'.
        """
        await self.connect()
        # Выбираем только нужные столбцы, исключая full_name, address, phone_number
        query = """
            SELECT
                id,
                user_id,
                username,
                collection_photo_id,
                receipt_photo_id,
                status
            FROM
                participants
        """
        async with self.conn.execute(query) as cursor:
            rows = await cursor.fetchall()
            # Названия столбцов будут соответствовать запросу
            column_names = [description[0] for description in cursor.description]
            return column_names, rows