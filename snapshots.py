import time
import cv2

import settings


class SnapshotManager:
    def __init__(self, save_dir, confidence_threshold, delay, cooldown):
        self.save_dir = save_dir
        self.confidence_threshold = confidence_threshold
        self.delay = delay
        self.cooldown = cooldown
        self.first_seen = None
        self.last_snapshot = 0
        self.save_dir.mkdir(exist_ok=True)

    def person_detected(self, result):
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            if class_id == 0 and confidence >= self.confidence_threshold:
                return True
        return False

    def try_save(self, frame, result, warning=False):
        now = time.time()

        if not self.person_detected(result):
            self.first_seen = None
            return None

        if self.first_seen is None:
            self.first_seen = now

        if now - self.first_seen < self.delay:
            return None

        if now - self.last_snapshot < self.cooldown:
            return None

        prefix = "person"
        if warning and settings.MARK_UNKNOWN_SNAPSHOTS:
            prefix = "person_warning"
        path = self.save_dir / time.strftime(f"{prefix}_%Y-%m-%d_%H-%M-%S.jpg")
        cv2.imwrite(str(path), frame)

        self.last_snapshot = now
        self.first_seen = now
        return path