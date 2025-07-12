# utils/email_sender.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from aiogram import Bot
import io

# ИМПОРТИРУЕМ ПЕРЕМЕННЫЕ ИЗ ВАШЕГО CONFIG.PY
from config import SMTP_EMAIL, SMTP_PASSWORD, RECEIVER_EMAIL, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT

logger = logging.getLogger(__name__)


async def send_email_with_photos(bot: Bot, caption: str, file_ids: list[str]):
    """
    Отправляет email с прикрепленными фотографиями.
    Фотографии загружаются из Telegram по их file_id.
    """
    # Проверяем, настроены ли все необходимые переменные для отправки email
    # Используем ваши имена переменных из config.py
    if not all([SMTP_EMAIL, SMTP_PASSWORD, RECEIVER_EMAIL, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT]):
        logger.warning("Настройки email не полностью указаны в config.py. Отправка email пропущена.")
        return

    msg = MIMEMultipart()
    msg['From'] = SMTP_EMAIL  # Используем вашу переменную
    msg['To'] = RECEIVER_EMAIL  # Используем вашу переменную
    msg['Subject'] = f"Новая заявка на ChocoWow: {caption}"

    # Добавляем текстовое содержимое письма
    msg.attach(MIMEBase('text', 'plain', charset='utf-8', _payload=caption))

    # Прикрепляем фотографии
    for i, file_id in enumerate(file_ids):
        try:
            # Получаем File объект из Telegram
            file_info = await bot.get_file(file_id)
            # Скачиваем файл в BytesIO буфер
            file_buffer = io.BytesIO()
            await bot.download_file(file_info.file_path, destination=file_buffer)
            file_buffer.seek(0)  # Переводим указатель в начало буфера

            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file_buffer.read())
            encoders.encode_base64(part)

            # Определяем расширение файла, если возможно, или используем общее
            file_extension = file_info.file_path.split('.')[-1] if '.' in file_info.file_path else 'jpg'
            part.add_header('Content-Disposition', f'attachment; filename=photo_{i + 1}.{file_extension}')
            msg.attach(part)
        except Exception as e:
            logger.error(f"Не удалось прикрепить фото {file_id} к email: {e}")

    # Отправляем письмо
    try:
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:  # Используем ваши переменные
            server.starttls()  # Для шифрованного соединения
            server.login(SMTP_EMAIL, SMTP_PASSWORD)  # Используем ваши переменные
            server.send_message(msg)
        logger.info(f"Email с заявкой отправлен на {RECEIVER_EMAIL}")  # Используем вашу переменную
    except Exception as e:
        logger.error(f"Ошибка при отправке email: {e}")