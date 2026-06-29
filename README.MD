# YOLO detector

Минимальный старт:

```bash
pip install -r requirements.txt
python build_face_db.py
python app.py
```

Фотографии сотрудников хранятся в `dataset/<имя>/`. Скрипт `build_face_db.py` создает локальную базу лиц `employees.pkl`, которую приложение использует для подписи людей на кадре.
