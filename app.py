import cv2
from ultralytics import YOLO

import settings
from classes import CLASS_GROUPS, MODES
from reporter import Reporter
from snapshots import SnapshotManager
from ui import setup_window, draw_status

model = YOLO(settings.MODEL_PATH)

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

        snapshot_path = snapshots.try_save(frame, result)
        if snapshot_path:
            print(f"Saved snapshot: {snapshot_path}")

        archive_path = reporter.tick()
        if archive_path:
            print(f"Sent archive: {archive_path}")

        annotated_frame = result.plot()
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