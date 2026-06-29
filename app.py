import cv2
from ultralytics import YOLO

import settings
from classes import CLASS_GROUPS, MODES
from employee_faces import EmployeeFaceRecognizer, draw_detection_labels, draw_face_labels
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

        if face_recognizer:
            face_matches = face_recognizer.identify_people(
                frame,
                result,
                settings.PERSON_CONFIDENCE_THRESHOLD,
            )
            draw_face_labels(snapshot_frame, face_matches)

        draw_detection_labels(annotated_frame, result, face_matches)

        snapshot_path = snapshots.try_save(snapshot_frame, result)
        if snapshot_path:
            print(f"Saved snapshot: {snapshot_path}")

        archive_path = reporter.tick()
        if archive_path:
            print(f"Sent archive: {archive_path}")

        draw_status(annotated_frame, mode)
        cv2.imshow(settings.WINDOW_NAME, annotated_frame)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break
        elif key in (ord("1"), ord("2"), ord("3"), ord("4")):
            mode_index = key - ord("1")
finally:
    camera.release()
    cv2.destroyAllWindows()
