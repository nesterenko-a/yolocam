# Repository Guidelines

## Project Structure & Module Organization
This is a compact Python YOLO detector application. The entry point is `app.py`, which opens the camera, loads `yolo11n.pt`, runs detection, saves snapshots, and sends reports. Configuration lives in `settings.py`. Supporting modules are split by responsibility: `classes.py` defines YOLO class groups and modes, `snapshots.py` manages image capture, `reporter.py` coordinates report sending, `notifiers.py` handles email/Telegram delivery, `archive_utils.py` creates archives, and `ui.py` owns OpenCV window/status drawing.

Runtime output is stored in `snapshots/` and `archives/`. Training or reference images are under `dataset/<person>/`, using filenames such as `person_2026-06-29_14-50-56.jpg`.

## Build, Test, and Development Commands
- `pip install -r requirements.txt`: install YOLO, OpenCV, notification, and face-recognition dependencies.
- `python build_face_db.py`: create `employees.pkl` from `dataset/<person>/` reference photos.
- `python app.py`: run the detector directly with the active camera and local settings.
- `run.bat`: Windows convenience launcher that sets notification variables before starting the app.
- `./run.sh`: Unix-style launcher with the same environment setup.

There is no package build step or dependency lock file. If dependencies change, update `requirements.txt` and `README.MD`.

## Coding Style & Naming Conventions
Use standard Python style: 4-space indentation, clear `snake_case` names for functions and variables, and `UPPER_SNAKE_CASE` for settings constants. Keep modules focused, matching the current responsibility-based layout. Prefer `pathlib.Path` for filesystem paths, as used in `settings.py`.

Avoid broad refactors when making feature changes. Keep camera, model, snapshot, reporting, and UI concerns separated.

## Testing Guidelines
No automated tests are present. For logic that can run without a camera, add tests under a new `tests/` directory using `pytest`, with filenames like `test_snapshots.py` or `test_archive_utils.py`. Prefer unit tests for archive creation, snapshot cooldown logic, and notifier behavior with mocked network calls.

Before opening a pull request, manually run `python app.py` on a machine with a camera and verify detection, snapshot saving, and report delivery settings.

## Commit & Pull Request Guidelines
Recent commits use short, imperative-style summaries such as `refactor code`, `add telegram bot`, and `yolo init`. Continue with concise messages that describe the main change.

Pull requests should include a brief description, manual test notes, and any configuration changes. Include screenshots or sample saved images when UI overlays, detection modes, or snapshot behavior changes. Link related issues when available.

## Security & Configuration Tips
Do not commit real bot tokens, email passwords, chat IDs, or personal addresses. Prefer local environment variables or an ignored `.env` file. If credentials have been committed, rotate them before sharing the repository.
