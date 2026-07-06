import smtplib
import requests
from email.message import EmailMessage

import runtime_settings
import settings


def _token():
    return runtime_settings.get("telegram_token") or settings.TELEGRAM_BOT_TOKEN


def _chat_id():
    return runtime_settings.get("telegram_chat_id") or settings.TELEGRAM_CHAT_ID


def _email_from():
    return runtime_settings.get("email_from") or settings.EMAIL_FROM


def _email_password():
    return runtime_settings.get("email_password") or settings.EMAIL_PASSWORD


def _email_to():
    return runtime_settings.get("email_to") or settings.EMAIL_TO


def send_email_archive(archive_path, settings):
    try:
        message = EmailMessage()
        message["From"] = _email_from()
        message["To"] = _email_to()
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
            smtp.login(_email_from(), _email_password())
            smtp.send_message(message)
    except Exception as e:
        print(f"Email archive send failed: {e}")

def send_telegram_archive(archive_path, settings):
    try:
        url = f"https://api.telegram.org/bot{_token()}/sendDocument"

        with open(archive_path, "rb") as file:
            response = requests.post(
                url,
                data={"chat_id": _chat_id()},
                files={"document": file},
                timeout=10,
            )

        response.raise_for_status()
    except Exception as e:
        print(f"Telegram archive send failed: {e}")


def send_email_image(image_path, settings, subject="YOLO alert"):
    try:
        message = EmailMessage()
        message["From"] = _email_from()
        message["To"] = _email_to()
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
            smtp.login(_email_from(), _email_password())
            smtp.send_message(message)
    except Exception as e:
        print(f"Email alert send failed: {e}")


def send_telegram_image(image_path, settings, caption="YOLO alert"):
    try:
        url = f"https://api.telegram.org/bot{_token()}/sendPhoto"

        with open(image_path, "rb") as file:
            response = requests.post(
                url,
                data={"chat_id": _chat_id(), "caption": caption},
                files={"photo": file},
                timeout=10,
            )

        response.raise_for_status()
    except Exception as e:
        print(f"Telegram alert send failed: {e}")


def send_email_video(video_path, settings, subject="YOLO video alert"):
    try:
        message = EmailMessage()
        message["From"] = _email_from()
        message["To"] = _email_to()
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
            smtp.login(_email_from(), _email_password())
            smtp.send_message(message)
    except Exception as e:
        print(f"Email video send failed: {e}")


def send_telegram_video(video_path, settings, caption="YOLO video alert"):
    try:
        url = f"https://api.telegram.org/bot{_token()}/sendVideo"

        with open(video_path, "rb") as file:
            response = requests.post(
                url,
                data={"chat_id": _chat_id(), "caption": caption},
                files={"video": file},
                timeout=60,
            )

        response.raise_for_status()
    except Exception as e:
        print(f"Telegram video send failed: {e}")