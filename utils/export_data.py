# utils/export_data.py

import csv
import io
import asyncio
from datetime import datetime
from aiogram import Bot  # Импортируем Bot для получения информации о файлах

# Базовый URL для скачивания файлов Telegram.
# BOT_TOKEN будет добавлен динамически в функции.
TELEGRAM_FILE_BASE_URL = "https://api.telegram.org/file/bot"


async def generate_participants_csv(
        column_names: list[str],
        data: list[tuple],
        bot: Bot  # Добавляем аргумент bot
) -> io.BytesIO:
    """
    Генерирует CSV-файл из предоставленных данных, заменяя ID фото на URL-ссылки,
    и возвращает его в виде BytesIO объекта.
    Эта операция выполняется в отдельном потоке, чтобы не блокировать основной асинхронный цикл.
    """

    bot_token = bot.token
    telegram_file_url_prefix = f"{TELEGRAM_FILE_BASE_URL}{bot_token}/"

    # Подготавливаем данные: заменяем ID фото на их URL
    processed_data = []
    # Определяем индексы для фотоколонок, чтобы знать, какие данные заменять
    collection_photo_idx = -1
    receipt_photo_idx = -1
    try:
        collection_photo_idx = column_names.index("collection_photo_id")
    except ValueError:
        pass
    try:
        receipt_photo_idx = column_names.index("receipt_photo_id")
    except ValueError:
        pass

    for row_tuple in data:
        row_list = list(row_tuple)  # Копируем в список для изменения

        # Получаем file_path и формируем URL для фото коллекции
        if collection_photo_idx != -1 and row_list[collection_photo_idx]:
            file_id = row_list[collection_photo_idx]
            try:
                file_info = await bot.get_file(file_id)
                row_list[collection_photo_idx] = f"{telegram_file_url_prefix}{file_info.file_path}"
            except Exception:
                row_list[collection_photo_idx] = f"Не удалось получить ссылку: {file_id}"  # Обработка ошибок

        # Получаем file_path и формируем URL для фото чека
        if receipt_photo_idx != -1 and row_list[receipt_photo_idx]:
            file_id = row_list[receipt_photo_idx]
            try:
                file_info = await bot.get_file(file_id)
                row_list[receipt_photo_idx] = f"{telegram_file_url_prefix}{file_info.file_path}"
            except Exception:
                row_list[receipt_photo_idx] = f"Не удалось получить ссылку: {file_id}"  # Обработка ошибок

        processed_data.append(tuple(row_list))  # Добавляем обработанную строку обратно как кортеж

    # Изменяем названия столбцов для вывода в CSV
    display_column_names = [col for col in column_names]
    if collection_photo_idx != -1:
        display_column_names[collection_photo_idx] = "collection_photo_url"
    if receipt_photo_idx != -1:
        display_column_names[receipt_photo_idx] = "receipt_photo_url"

    # Теперь генерируем CSV в отдельном потоке
    # (Эта функция должна быть синхронной, так как она вызывается через asyncio.to_thread)
    def _generate_sync_csv():
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(display_column_names)  # Записываем измененные заголовки
        for row in processed_data:  # Записываем уже обработанные данные
            writer.writerow(row)

        return output.getvalue().encode('utf-8')

    csv_bytes = await asyncio.to_thread(_generate_sync_csv)

    return io.BytesIO(csv_bytes)