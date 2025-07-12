import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# --- Настройки базы данных ---
DB_NAME = "promo.db"  # Имя файла базы данных SQLite

# --- Основные настройки бота ---
# Загрузка токена бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Загрузка ID администраторов
raw_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(admin_id.strip()) for admin_id in raw_admin_ids.split(',')] if raw_admin_ids else []

# --- Настройки почты ---
# Эти переменные загружаются из .env
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

# ДОБАВЬТЕ ЭТИ ДВЕ СТРОКИ!
# Они должны быть загружены из .env и затем доступны для импорта из config.py
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER") # Убедитесь, что это имя соответствует вашему .env
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT")) # Убедитесь, что это имя соответствует вашему .env и что оно int

# --- Настройки файловой системы ---
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "data/uploads")

# Проверка наличия обязательных переменных
if not BOT_TOKEN or not ADMIN_IDS:
    raise ValueError("Ошибка: BOT_TOKEN и ADMIN_IDS должны быть указаны в .env файле.")

# Дополнительная проверка для почты, если вы её используете
if (SMTP_EMAIL and SMTP_PASSWORD and RECEIVER_EMAIL and EMAIL_SMTP_SERVER and EMAIL_SMTP_PORT) is None:
    print("Предупреждение: Не все настройки SMTP почты указаны в .env, отправка email может не работать.")