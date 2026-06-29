import cv2
from ultralytics import YOLO

import settings
from classes import CLASS_GROUPS, MODES
from employee_faces import EmployeeFaceRecognizer, draw_detection_labels, draw_face_labels
from notifiers import send_email_image, send_telegram_image
from policies import Action, PolicyEngine
from reporter import Reporter
from snapshots import SnapshotManager
from ui import setup_window, draw_status

model = YOLO(settings.MODEL_PATH)
face_recognizer = None

if settings.FACE_RECOGNITION_ENABLED:
    face_recognizer = EmployeeFaceRecognizer(
        settings.FACE_DB_PATH,
        settings.FACE_SIMILARITY_THRESHOLD,
        settings.FACE_DETECTION_SIZE,
    )
    if not settings.FACE_DB_PATH.exists():
        print(f"Face database not found: {settings.FACE_DB_PATH}. Run build_face_db.py first.")

policy_engine = PolicyEngine(
    settings.POLICIES,
    settings.POLICY_DEFAULT,
    settings.POLICY_ALERT_COOLDOWN_SECONDS,
)

camera = cv2.VideoCapture(settings.CAMERA_INDEX)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAMERA_WIDTH)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAMERA_HEIGHT)

setup_window(settings.WINDOW_NAME, settings.FULLSCREEN)

snapshots = SnapshotManager(
    settings.SAVE_DIR,
    settings.PERSON_CONFIDENCE_THRESHOLD,
    settings.SNAPSHOT_AFTER_SECONDS,
    settings.SNAPSHOT_COOLDOWN_SECONDS,
)

reporter = Reporter(settings.SAVE_DIR, settings.ARCHIVE_DIR, settings)

mode_index = 0
face_recognition_active = bool(face_recognizer)

try:
    while True:
        ok, frame = camera.read()
        if not ok:
            break

        mode = MODES[mode_index]
        results = model(frame, classes=CLASS_GROUPS[mode], verbose=False)
        result = results[0]

        annotated_frame = result.plot(labels=False, conf=False)
        snapshot_frame = frame.copy()
        face_matches = []

        if face_recognizer and face_recognition_active:
            face_matches = face_recognizer.identify_people(
                frame,
                result,
                settings.PERSON_CONFIDENCE_THRESHOLD,
            )
            draw_face_labels(snapshot_frame, face_matches)

        draw_detection_labels(annotated_frame, result, face_matches)

        # Resolve policy actions for every detected person in this frame
        actions = {policy_engine.get_action(m.name) for m in face_matches}
        if not face_matches and snapshots.person_detected(result):
            actions.add(policy_engine.get_action("NO_FACE"))

        should_save = any(a != Action.NONE for a in actions)
        should_alert = any(a in (Action.ALERT, Action.ALERT_AND_ARCHIVE) for a in actions)
        exclude_from_archive = actions.isdisjoint({Action.ARCHIVE, Action.ALERT_AND_ARCHIVE})

        if should_save:
            snapshot_path = snapshots.try_save(snapshot_frame, result)
            if snapshot_path:
                print(f"Saved snapshot: {snapshot_path}")
                if should_alert:
                    alert_name = next(
                        (m.name for m in face_matches
                         if policy_engine.get_action(m.name) in (Action.ALERT, Action.ALERT_AND_ARCHIVE)),
                        "UNKNOWN",
                    )
                    if policy_engine.can_alert(alert_name):
                        alert_text = f"YOLO alert: {alert_name}"
                        send_email_image(snapshot_path, settings, subject=alert_text)
                        send_telegram_image(snapshot_path, settings, caption=alert_text)
                        print(alert_text)
                        if exclude_from_archive:
                            reporter.mark_sent(snapshot_path)
                            snapshot_path.unlink()

        archive_path = reporter.tick()
        if archive_path:
            print(f"Sent archive: {archive_path}")

        draw_status(annotated_frame, mode, face_recognition_active)
        cv2.imshow(settings.WINDOW_NAME, annotated_frame)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break
        elif key in (ord("1"), ord("2"), ord("3"), ord("4")):
            mode_index = key - ord("1")
        elif key == ord("5") and face_recognizer:
            face_recognition_active = not face_recognition_active
            label = "ON" if face_recognition_active else "OFF"
            print(f"Face recognition: {label}")
finally:
    camera.release()
    cv2.destroyAllWindows()
