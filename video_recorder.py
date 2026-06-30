import time
import cv2

import settings

FORMATS = {
    "avi":  ("XVID", ".avi"),
    "mp4":  ("mp4v", ".mp4"),
    "mkv":  ("XVID", ".mkv"),
    "mov":  ("mp4v", ".mov"),
    "flv":  ("FLV1", ".flv"),
}


class VideoRecorder:
    def __init__(self):
        settings.VIDEO_DIR.mkdir(exist_ok=True)
        self.writer = None
        self.start_time = None
        self.path = None

    def start(self, frame):
        if self.writer:
            return
        fmt = FORMATS.get(settings.VIDEO_FORMAT, FORMATS["avi"])
        fps = 20
        h, w = frame.shape[:2]
        ext = fmt[1]
        self.path = settings.VIDEO_DIR / time.strftime(f"alert_%Y-%m-%d_%H-%M-%S{ext}")
        fourcc = cv2.VideoWriter_fourcc(*fmt[0])
        writer = cv2.VideoWriter(str(self.path), fourcc, fps, (w, h))
        if not writer.isOpened():
            print(f"Codec {fmt[0]} for .{ext} not available, falling back to XVID")
            self.path = self.path.with_suffix(".avi")
            writer = cv2.VideoWriter(str(self.path), cv2.VideoWriter_fourcc(*"XVID"), fps, (w, h))
        self.writer = writer
        self.writer.write(frame)
        self.start_time = time.time()

    def write(self, frame):
        if not self.writer:
            return True
        self.writer.write(frame)
        if time.time() - self.start_time >= settings.VIDEO_MAX_DURATION:
            return False
        return True

    def stop(self):
        if not self.writer:
            return None
        self.writer.release()
        self.writer = None
        path = self.path
        self.path = None
        return path

    @property
    def active(self):
        return self.writer is not None
