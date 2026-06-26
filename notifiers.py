import smtplib
import requests
from email.message import EmailMessage

def send_email_archive(archive_path, settings):
    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = settings.EMAIL_TO
    message["Subject"] = "YOLO snapshots archive"
    message.set_content("Archive with YOLO snapshots.")

    with open(archive_path, "rb") as file:
        message.add_attachment(
            file.read(),
            maintype="application",
            subtype="zip",
            filename=archive_path.name,
        )

    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(settings.EMAIL_FROM, settings.EMAIL_PASSWORD)
        smtp.send_message(message)

def send_telegram_archive(archive_path, settings):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"

    with open(archive_path, "rb") as file:
        response = requests.post(
            url,
            data={"chat_id": settings.TELEGRAM_CHAT_ID},
            files={"document": file},
            timeout=60,
        )

    response.raise_for_status()