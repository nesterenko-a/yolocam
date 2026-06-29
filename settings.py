import os
from pathlib import Path
from policies import Action

# --- YOLO и камера ---
MODEL_PATH = "yolo11n.pt"                 # файл весов YOLO (nano), скачивается автоматически
CAMERA_INDEX = 0                          # индекс камеры (0 = встроенная)
WINDOW_NAME = "YOLO detector"             # заголовок окна OpenCV
CAMERA_WIDTH = 1280                       # ширина кадра
CAMERA_HEIGHT = 720                       # высота кадра
FULLSCREEN = False                        # полноэкранный режим окна

# --- Директории ---
SAVE_DIR = Path("snapshots")              # куда сохраняются снимки с людьми
ARCHIVE_DIR = Path("archives")            # куда складываются ZIP-архивы перед отправкой
DATASET_DIR = Path("dataset")             # папка с эталонными фото сотрудников (<имя>/)
FACE_DB_PATH = Path("employees.pkl")      # файл базы лиц (создаётся build_face_db.py)

# --- Снимки ---
PERSON_CONFIDENCE_THRESHOLD = 0.75        # минимальная уверенность YOLO для класса "person"
SNAPSHOT_AFTER_SECONDS = 0.2              # задержка перед первым снимком после появления человека
SNAPSHOT_COOLDOWN_SECONDS = 5             # пауза между повторными снимками одного человека

# --- Распознавание лиц ---
FACE_RECOGNITION_ENABLED = True           # вкл/выкл распознавание лиц (InsightFace)
FACE_SIMILARITY_THRESHOLD = 0.45          # порог косинусного сходства (выше = строже)
FACE_DETECTION_SIZE = (640, 640)          # размер кадра для детектора лиц (меньше = быстрее)

# --- Отправка ---
SEND_EMAIL = True                         # отправлять архивы/тревоги по email
SEND_TELEGRAM = True                      # отправлять архивы/тревоги в Telegram
REPORT_EVERY_SECONDS = 3600               # как часто формировать часовой архив (3600 = 1 час)

# --- Email (Gmail SMTP) ---
EMAIL_FROM = os.getenv("YOLO_EMAIL_FROM", "")         # от кого
EMAIL_PASSWORD = os.getenv("YOLO_EMAIL_PASSWORD", "") # пароль приложения Gmail
EMAIL_TO = os.getenv("YOLO_EMAIL_TO", "")             # кому
SMTP_SERVER = "smtp.gmail.com"                        # сервер Gmail
SMTP_PORT = 587                                       # порт TLS

# --- Telegram Bot ---
TELEGRAM_BOT_TOKEN = os.getenv("YOLO_TELEGRAM_BOT_TOKEN", "")  # токен бота (от BotFather)
TELEGRAM_CHAT_ID = os.getenv("YOLO_TELEGRAM_CHAT_ID", "")      # ID чата для отправки

# --- Политики обработки ---
POLICIES: dict[str, Action] = {
    "UNKNOWN": Action.ALERT,        # неопознанный → мгновенная тревога
    "NO_FACE": Action.ARCHIVE,      # лицо не найдено → в часовой архив
}
POLICY_DEFAULT = Action.ARCHIVE               # действие по умолчанию для остальных (известные сотрудники)
POLICY_ALERT_COOLDOWN_SECONDS = 10            # пауза между тревогами для одного и того же человека
