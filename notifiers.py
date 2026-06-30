import smtplib
import requests
from email.message import EmailMessage

def send_email_archive(archive_path, settings):
    try:
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

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(settings.EMAIL_FROM, settings.EMAIL_PASSWORD)
            smtp.send_message(message)
    except Exception as e:
        print(f"Email archive send failed: {e}")

def send_telegram_archive(archive_path, settings):
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"

        with open(archive_path, "rb") as file:
            response = requests.post(
                url,
                data={"chat_id": settings.TELEGRAM_CHAT_ID},
                files={"document": file},
                timeout=10,
            )

        response.raise_for_status()
    except Exception as e:
        print(f"Telegram archive send failed: {e}")


def send_email_image(image_path, settings, subject="YOLO alert"):
    try:
        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = settings.EMAIL_TO
        message["Subject"] = subject
        message.set_content("YOLO snapshot attached.")

        with open(image_path, "rb") as file:
            message.add_attachment(
                file.read(),
                maintype="image",
                subtype="jpeg",
                filename=image_path.name,
            )

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(settings.EMAIL_FROM, settings.EMAIL_PASSWORD)
            smtp.send_message(message)
    except Exception as e:
        print(f"Email alert send failed: {e}")


def send_telegram_image(image_path, settings, caption="YOLO alert"):
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendPhoto"

        with open(image_path, "rb") as file:
            response = requests.post(
                url,
                data={"chat_id": settings.TELEGRAM_CHAT_ID, "caption": caption},
                files={"photo": file},
                timeout=10,
            )

        response.raise_for_status()
    except Exception as e:
        print(f"Telegram alert send failed: {e}")


def send_email_video(video_path, settings, subject="YOLO video alert"):
    try:
        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = settings.EMAIL_TO
        message["Subject"] = subject
        message.set_content("YOLO video attached.")

        video_type = video_path.suffix.lstrip(".") or "avi"

        with open(video_path, "rb") as file:
            message.add_attachment(
                file.read(),
                maintype="video",
                subtype=video_type,
                filename=video_path.name,
            )

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(settings.EMAIL_FROM, settings.EMAIL_PASSWORD)
            smtp.send_message(message)
    except Exception as e:
        print(f"Email video send failed: {e}")


def send_telegram_video(video_path, settings, caption="YOLO video alert"):
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendVideo"

        with open(video_path, "rb") as file:
            response = requests.post(
                url,
                data={"chat_id": settings.TELEGRAM_CHAT_ID, "caption": caption},
                files={"video": file},
                timeout=60,
            )

        response.raise_for_status()
    except Exception as e:
        print(f"Telegram video send failed: {e}")