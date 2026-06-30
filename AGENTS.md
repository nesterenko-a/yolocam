# YOLO Detector — Agent Guidelines

## Entrypoint & Setup Order
- `app.py` — main loop: open camera → YOLO inference → face recognition → snapshot → report → UI.
- `settings.py` — all configuration constants; credentials come from env vars (`YOLO_EMAIL_*`, `YOLO_TELEGRAM_*`).
- **Must run `python build_face_db.py` before `app.py`** to create `employees.pkl` from `dataset/<person>/` images.
- YOLO model used: `yolo11n.pt` (nano variant, downloaded automatically by ultralytics).

## Module Responsibilities
| File | Role |
|---|---|
| `classes.py` | Detection mode groups: `people`, `animals`, `objects`, `all` |
| `snapshots.py` | Cooldown-gated JPEG capture (0.2s delay, 2s cooldown) |
| `employee_faces.py` | InsightFace `buffalo_l` face recognition (CPU), draws all detection labels on frames |
| `policies.py` | `Action` enum + `PolicyEngine` with per-person cooldown gating |
| `reporter.py` | Zips new snapshots hourly (`REPORT_EVERY_SECONDS=3600`), sends via email/Telegram, **deletes sent files** |
| `notifiers.py` | SMTP email (Gmail, TLS) and Telegram `sendDocument` API |
| `video_recorder.py` | Short video clips triggered by person detection |
| `web_stream.py` | Built-in HTTP MJPEG stream server (no extra deps) |
| `archive_utils.py` | ZIP creation in `archives/` |
| `ui.py` | OpenCV window + status bar with mode/help text |

## Face Recognition
- Uses InsightFace `buffalo_l` model with `CPUExecutionProvider`.
- Embedding similarity: **cosine similarity via dot product on L2-normalized vectors**.
- Threshold: `FACE_SIMILARITY_THRESHOLD=0.45`.

## Policy Layer
- `policies.py` — `Action` enum (`ARCHIVE`, `ALERT`, `NONE`, `ALERT_AND_ARCHIVE`) + `PolicyEngine` with per-person cooldown gating.
- `settings.py` config: `POLICIES` dict maps person name (or `"UNKNOWN"`, `"NO_FACE"`) to an `Action`. `POLICY_DEFAULT` fallback. `POLICY_ALERT_COOLDOWN_SECONDS` sets min gap between alerts for the same person.
- Frame-level resolution: if **any** detected person triggers `ALERT`/`ALERT_AND_ARCHIVE`, the whole frame generates an instant alert. Snapshot is skipped only if **all** detected people have `NONE`.
- `ALERT`-only snapshots are excluded from the hourly archive via `reporter.mark_sent()`.
- `notifiers.py` sends ZIP archives for hourly reports, individual JPEGs for instant alerts.

## Runtime Controls
- **Keys 1–4** switch detection modes; **Esc** exits.
- Snapshots saved to `snapshots/person_<date>.jpg`. Archives to `archives/snapshots_<date>.zip`.

## Commands
- `pip install -r requirements.txt` — note `pywin32` is Windows-only (conditional dep).
- `python build_face_db.py` — builds face database.
- `python app.py` — run detector.
- No tests, lint, typecheck, or formatter config exists. Add tests in `tests/` with `pytest` for camera-independent logic.

## Security Gotchas
- **`run.sh` is tracked in git and contains real credentials.** Do not push it. Prefer a `.env` file or env vars.
- `run.bat` is gitignored (same credentials, local convenience only).
- If credentials were committed, rotate them before sharing the repo.

## Coding Conventions
- 4-space indent, `snake_case` functions/vars, `UPPER_SNAKE_CASE` settings constants.
- Prefer `pathlib.Path` for filesystem paths.
- Keep camera, model, snapshot, reporting, and UI concerns separated.
