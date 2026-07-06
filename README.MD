# YOLO Detector — детекция объектов и лиц с камеры

Приложение для видеонаблюдения: обнаруживает людей, животных и предметы через YOLO, распознаёт лица сотрудников через InsightFace, сохраняет снимки и отправляет отчёты в Telegram / Email.

## Быстрый старт

```bash
pip install -r requirements.txt
python build_face_db.py          # создать базу лиц из dataset/
python app.py                    # запустить детектор
```

## Подготовка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

На Windows автоматически установится `pywin32`, на Linux/macOS — нет.

### 2. Добавление сотрудников

Положите фотографии лиц в папку `dataset/<имя_сотрудника>/`.  
Поддерживаемые форматы: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`.

Пример структуры:

```
dataset/
├── ivan/
│   ├── photo1.jpg
│   └── photo2.jpg
├── maria/
│   └── photo.jpg
└── petr/
    └── ...
```

### 3. Создание базы лиц

```bash
python build_face_db.py
```

Скрипт найдёт все лица в `dataset/`, извлечёт эмбеддинги (InsightFace `buffalo_l`) и сохранит в `employees.pkl`. Пропущенные изображения (нет лица, не читается) будут выведены в консоль.

### 4. Настройка уведомлений (опционально)

Уведомления работают через переменные окружения. Можно задать их вручную или через `run.bat` / `.env`:

| Переменная | Назначение |
|---|---|
| `YOLO_EMAIL_FROM` | Email отправителя (Gmail) |
| `YOLO_EMAIL_PASSWORD` | Пароль приложения Gmail |
| `YOLO_EMAIL_TO` | Email получателя |
| `YOLO_TELEGRAM_BOT_TOKEN` | Токен Telegram-бота (BotFather) |
| `YOLO_TELEGRAM_CHAT_ID` | ID чата для отправки |

> ⚠️ **Важно**: `run.sh` содержит реальные учетные данные и отслеживается git. Не пушите его. Используйте `.env` или переменные окружения.

## Запуск

```bash
python app.py
```

При запуске открывается окно с видеопотоком. Если база лиц не найдена — распознавание работать не будет, но детекция продолжится.

### Подключение IP-камеры (RTSP)

По умолчанию используется USB-камера (индекс 0). Для подключения сетевой камеры задайте переменную окружения `YOLO_CAMERA`:

```bash
# Linux
export YOLO_CAMERA=rtsp://user:pass@192.168.1.100:554/stream

# Windows PowerShell
$env:YOLO_CAMERA="rtsp://user:pass@192.168.1.100:554/stream"

# Docker
docker run -e YOLO_CAMERA=rtsp://192.168.1.100:554/stream ...
```

Поддерживаются любые URL, которые понимает OpenCV: `rtsp://...`, `http://...` (MJPEG), `rtmp://...`. При обрыве соединения камера автоматически переподключается через 3 секунды.

> Для HTTP MJPEG-потоков (`http://...`) используется `MJPEGReader` — прямой парсинг multipart-ответа без FFMPEG, что значительно быстрее стандартного `cv2.VideoCapture`.

### Отдельный сервер камеры

Если USB-камера на другой машине или в Docker (где нет доступа к `/dev/video0`), запустите `camera_server.py` — он транслирует камеру как MJPEG-поток по HTTP:

```bash
# На машине с камерой
python camera_server.py --port 8081

# На машине детектора
YOLO_CAMERA=http://192.168.1.50:8081/stream python app.py
```

Параметры: `--index` (индекс камеры, по умолч. 0), `--port` (порт, по умолч. 8081).

### Docker + camera_server (через интернет)

Камера и детектор могут быть в разных странах:

```bash
# 1. На машине с камерой (Франция) — сделать порт 8081 доступным извне:
python camera_server.py --port 8081

# 2. На сервере детектора (Финляндия) — передать URL камеры:
YOLO_CAMERA=http://<публичный-IP-Франции>:8081/stream docker compose -f docker/docker-compose.yml up -d
```

Или через `.env` файл рядом с `docker-compose.yml`:

```env
YOLO_CAMERA=http://51.15.xxx.xxx:8081/stream
YOLO_TELEGRAM_BOT_TOKEN=...
```

### Kubernetes (minikube)

**Требования:** `kubectl`, `minikube`, `python`, `pip install kubernetes`.

Порядок деплоя:

```bash
# 1. Убедиться, что employees.pkl есть в корне проекта (если нужны лица)
#    Если файла нет — распознавание работать не будет, остальное — да.

# 2. Установить Python-библиотеку для генерации манифестов
pip install kubernetes

# 3. Сгенерировать манифесты
#    camera_url — адрес camera_server.py (локальный или удалённый)
python generate_k8s.py --camera http://host.minikube.internal:8081/stream

# 4. Собрать и загрузить образ в minikube
docker build -t yolo-detector:latest -f docker/Dockerfile .
minikube image load yolo-detector:latest

# 5. Развернуть в кластер
kubectl apply -f k8s/

# 6. Открыть веб-стрим
minikube service yolo-detector -n yolo-detector --url
```

Или одной командой (если `camera_server` на `host.minikube.internal:8081`):

```bash
deploy_minikube.bat
# или с другим адресом камеры:
deploy_minikube.bat http://10.8.1.1:8081/stream
```

**Если лица не распознаются** — скопировать `employees.pkl` в под:

```bash
kubectl cp employees.pkl <имя-пода>:/app/ -n yolo-detector
kubectl delete pod -n yolo-detector <имя-пода>
```

## Управление

| Клавиша | Действие |
|---|---|
| `1` | Режим: только люди |
| `2` | Режим: только животные |
| `3` | Режим: только предметы |
| `4` | Режим: всё подряд |
| `5` | Вкл/Выкл распознавание лиц |
| `Esc` | Выход |

Статус-бар показывает текущий режим и состояние распознавания лиц.

## Как это работает

Общая схема цикла:

```
Камера → YOLO → распознавание лиц → политика → снимок + видео + отчёт
```

1. **YOLO** (`yolo11n.pt`) — детектирует объекты на кадре
2. **Распознавание лиц** (InsightFace `buffalo_l`) — определяет, кто из сотрудников в кадре
3. **Политики** — решают, что делать с каждым обнаруженным человеком
4. **Снимки** — сохраняются в `snapshots/` (с префиксом `person_warning` для неопознанных)
5. **Видео** — записывается до 5 секунд при обнаружении человека (только неопознанных, если включено)
6. **Отчёты** — раз в час ZIP-архив отправляется в Telegram и Email, видео отправляется сразу

## Политики обработки (policies)

Для каждого обнаруженного человека применяется действие в зависимости от того, известен он или нет.

Настраивается в `settings.py`:

```python
POLICIES = {
    "UNKNOWN": Action.ALERT,           # неопознанный → тревога
    "NO_FACE": Action.ARCHIVE,         # лицо не найдено → в часовой архив
}
POLICY_DEFAULT = Action.ARCHIVE        # известные сотрудники → часовой архив
POLICY_ALERT_COOLDOWN_SECONDS = 60     # пауза между тревогами для одного человека
```

Возможные действия:
- `ARCHIVE` — снимок уходит в часовой архив
- `ALERT` — мгновенная отправка снимка в Telegram/Email
- `NONE` — игнорировать (не сохранять, не отправлять)
- `ALERT_AND_ARCHIVE` — и тревога, и часовой архив

Если в кадре несколько человек с разными политиками — приоритет у самой строгой (ALERT выше ARCHIVE).

## Настройки (settings.py)

Все основные параметры вынесены в `settings.py`:

| Параметр | По умолчанию | Описание |
|---|---|---|
| `CAMERA_WIDTH / HEIGHT` | 1280×720 | Разрешение камеры |
| `PERSON_CONFIDENCE_THRESHOLD` | 0.75 | Минимальная уверенность YOLO для человека |
| `SNAPSHOT_AFTER_SECONDS` | 0.2 | Задержка перед первым снимком |
| `SNAPSHOT_COOLDOWN_SECONDS` | 5 | Пауза между снимками одного человека |
| `FACE_RECOGNITION_INTERVAL` | 1 | Раз в N кадров запускать распознавание лиц |
| `FACE_SIMILARITY_THRESHOLD` | 0.45 | Порог сходства лиц (выше = строже) |
| `VIDEO_ENABLED` | True | Записывать видео при обнаружении человека |
| `VIDEO_MAX_DURATION` | 5 | Макс. длина видео (сек) |
| `VIDEO_ON_UNKNOWN_ONLY` | True | Только для неопознанных |
| `VIDEO_FORMAT` | mkv | Формат: avi, mp4, mkv, mov, flv |
| `SEND_VIDEO_EMAIL` | True | Отправлять видео на почту |
| `SEND_VIDEO_TELEGRAM` | True | Отправлять видео в Telegram |
| `MARK_UNKNOWN_SNAPSHOTS` | True | Префикс `person_warning` в имени файла |
| `REPORT_EVERY_SECONDS` | 3600 | Период отправки архива |
| `FULLSCREEN` | False | Полноэкранный режим |
| `HEADLESS` | False | Работа без окна (например, на сервере) |
| `WEB_STREAM_ENABLED` | False | Веб-трансляция через браузер |
| `WEB_STREAM_PORT` | 8080 | Порт для веб-трансляции |

## Рекомендации

- **Для ускорения на слабых CPU**: уменьшите `CAMERA_WIDTH`/`CAMERA_HEIGHT` до 640×480, увеличьте `FACE_RECOGNITION_INTERVAL`.
- **Фотографии сотрудников**: достаточно 1–3 чётких фото на человека, лицо должно быть в кадре.
- **База лиц** (`employees.pkl`) пересоздаётся через `python build_face_db.py` — нужно запускать заново после добавления новых людей в `dataset/`.
- **Учётные данные**: не храните токены и пароли в git. Используйте `.env` файл (он в `.gitignore`).
- **Архивы**: отправленные ZIP-файлы и ALERT-снимки удаляются автоматически. Часовые отчёты хранятся только в момент отправки.
- **Видео**: записывается при появлении человека, отправляется сразу после остановки, затем удаляется. По умолчанию только для неопознанных (`VIDEO_ON_UNKNOWN_ONLY = True`).
- **Распознавание лиц** работает на CPU. Для ускорения можно переключить InsightFace на GPU (`providers` в `EmployeeFaceRecognizer`).

## Структура проекта

```
├── app.py              # Главный цикл
├── settings.py         # Конфигурация
├── classes.py          # Группы классов YOLO
├── policies.py         # Политики обработки
├── employee_faces.py   # Распознавание лиц (InsightFace)
├── video_recorder.py   # Запись видео при тревоге
├── snapshots.py        # Менеджер снимков
├── reporter.py         # Отправка отчётов
├── notifiers.py        # Email / Telegram
├── archive_utils.py    # ZIP-архивы
├── ui.py               # Окно и статус-бар
├── build_face_db.py    # Сборка базы лиц
└── requirements.txt    # Зависимости
```

## Требования

- Python 3.10+
- Веб-камера (или любая камера, совместимая с OpenCV)
- 4+ GB RAM (InsightFace + YOLO одновременно)
