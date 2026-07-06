"""
Настройки времени выполнения (только в памяти, без сохранения).
Значения по умолчанию — из settings.py, сбрасываются при перезапуске.
"""

import os
from pathlib import Path

import settings

DEFAULTS = {
    "camera_url": "",
    "face_enabled": True,
    "mode_index": 0,
    "send_email": bool(settings.SEND_EMAIL),
    "send_telegram": bool(settings.SEND_TELEGRAM),
    "video_enabled": bool(settings.VIDEO_ENABLED),
    "send_video_email": bool(settings.SEND_VIDEO_EMAIL),
    "send_video_telegram": bool(settings.SEND_VIDEO_TELEGRAM),
    "policy_alert": True,
    "telegram_token": "",
    "telegram_chat_id": "",
    "email_from": "",
    "email_password": "",
    "email_to": "",
}

_config = dict(DEFAULTS)


def get(key):
    return _config.get(key)


def set(key, value):
    _config[key] = value


def all():
    return dict(_config)


def reset():
    _config.clear()
    _config.update(DEFAULTS)
