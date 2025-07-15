# config.py

import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = "promo.db"
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID главного администратора
raw_main_admin_id = os.getenv("MAIN_ADMIN_ID")
if raw_main_admin_id and raw_main_admin_id.isdigit():
    MAIN_ADMIN_ID = int(raw_main_admin_id)
else:
    raise ValueError("Ошибка: MAIN_ADMIN_ID должен быть указан в .env файле и быть числом.")

# Ссылка на канал с результатами
RESULTS_CHANNEL_LINK = os.getenv("RESULTS_CHANNEL_LINK")

# Настройки почты
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
raw_port = os.getenv("EMAIL_SMTP_PORT")
EMAIL_SMTP_PORT = int(raw_port) if raw_port and raw_port.isdigit() else 587

# Проверки
if not BOT_TOKEN:
    raise ValueError("Ошибка: BOT_TOKEN должен быть указан в .env файле.")
if not RESULTS_CHANNEL_LINK:
    print("Предупреждение: RESULTS_CHANNEL_LINK не указан в .env, отправка результатов может не работать.")