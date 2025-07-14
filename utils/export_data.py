
import csv
import io
import asyncio
import json
from aiogram import Bot

TELEGRAM_FILE_BASE_URL = "https://api.telegram.org/file/bot"


async def generate_participants_csv(
        column_names: list[str],
        data: list[tuple],
        bot: Bot
) -> io.BytesIO:
    bot_token = bot.token
    telegram_file_url_prefix = f"{TELEGRAM_FILE_BASE_URL}{bot_token}/"

    processed_data = []

    # Get indexes of file columns
    try:
        collection_idx = column_names.index("collection_photo_ids")
        receipt_idx = column_names.index("receipt_file_ids")
    except ValueError as e:
        print(f"Error finding column index: {e}")
        return io.BytesIO()  # Return empty if columns not found

    for row_tuple in data:
        row_list = list(row_tuple)

        # Process collection photos
        if row_list[collection_idx]:
            try:
                file_ids = json.loads(row_list[collection_idx])
                urls = []
                for file_id in file_ids:
                    try:
                        file_info = await bot.get_file(file_id)
                        urls.append(f"{telegram_file_url_prefix}{file_info.file_path}")
                    except Exception:
                        urls.append(f"Invalid_file_id: {file_id}")
                row_list[collection_idx] = "\n".join(urls)  # Join URLs with newline
            except (json.JSONDecodeError, TypeError):
                row_list[collection_idx] = "Invalid JSON data"

        # Process receipt files
        if row_list[receipt_idx]:
            try:
                file_ids = json.loads(row_list[receipt_idx])
                urls = []
                for file_id in file_ids:
                    try:
                        file_info = await bot.get_file(file_id)
                        urls.append(f"{telegram_file_url_prefix}{file_info.file_path}")
                    except Exception:
                        urls.append(f"Invalid_file_id: {file_id}")
                row_list[receipt_idx] = "\n".join(urls)  # Join URLs with newline
            except (json.JSONDecodeError, TypeError):
                row_list[receipt_idx] = "Invalid JSON data"

        processed_data.append(tuple(row_list))

    display_column_names = list(column_names)
    display_column_names[collection_idx] = "collection_photo_urls"
    display_column_names[receipt_idx] = "receipt_file_urls"

    # Using synchronous function in thread for CSV generation
    def _generate_sync_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(display_column_names)
        writer.writerows(processed_data)
        return output.getvalue().encode('utf-8')

    csv_bytes = await asyncio.to_thread(_generate_sync_csv)
    return io.BytesIO(csv_bytes)
