
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import logging
from aiogram import Bot
import io

from config import SMTP_EMAIL, SMTP_PASSWORD, RECEIVER_EMAIL, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT

logger = logging.getLogger(__name__)

async def send_email_with_files(bot: Bot, caption: str, file_ids: list[str]):
    if not all([SMTP_EMAIL, SMTP_PASSWORD, RECEIVER_EMAIL, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT]):
        logger.warning("Настройки email не полностью указаны. Отправка email пропущена.")
        return

    msg = MIMEMultipart()
    msg['From'] = SMTP_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"Новая заявка ChocoWow: {caption}"

    msg.attach(MIMEText(caption, 'plain'))

    for i, file_id in enumerate(file_ids):
        try:
            file_info = await bot.get_file(file_id)
            file_buffer = io.BytesIO()
            await bot.download_file(file_info.file_path, destination=file_buffer)
            file_buffer.seek(0)

            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file_buffer.read())
            encoders.encode_base64(part)

            file_extension = file_info.file_path.split('.')[-1]
            filename = f"file_{i + 1}.{file_extension}"
            part.add_header('Content-Disposition', f'attachment; filename={filename}')
            msg.attach(part)
        except Exception as e:
            logger.error(f"Не удалось прикрепить файл {file_id} к email: {e}")

    try:
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email с заявкой отправлен на {RECEIVER_EMAIL}")
    except Exception as e:
        logger.error(f"Ошибка при отправке email: {e}")
