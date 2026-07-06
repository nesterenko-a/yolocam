"""
Читает MJPEG-поток через HTTP напрямую (без OpenCV VideoCapture).
Это быстрее, чем cv2.VideoCapture("http://..."), который использует FFMPEG.

Использование:
    reader = MJPEGReader("http://localhost:8081/stream")
    ok, frame = reader.read()
"""

import io
import threading
import time
from urllib.request import urlopen

import cv2
import numpy as np


class MJPEGReader:
    def __init__(self, url, max_fps=30):
        self._url = url
        self._frame = None
        self._lock = threading.Lock()
        self._running = True
        self._stream = None
        self._buf = b""
        self._boundary = None

        thread = threading.Thread(target=self._fetch, daemon=True)
        thread.start()
        time.sleep(0.5)

    def _fetch(self):
        try:
            self._stream = urlopen(self._url)
            content_type = self._stream.headers.get("Content-Type", "")
            if "boundary=" in content_type:
                self._boundary = content_type.split("boundary=")[-1].strip().encode()
        except Exception as e:
            print(f"MJPEGReader: connection failed: {e}")
            self._running = False
            return

        while self._running:
            try:
                chunk = self._stream.read(65536)
                if not chunk:
                    break
                self._buf += chunk
                self._parse_frames()
            except Exception:
                break

        self._running = False

    def _parse_frames(self):
        if self._boundary is None or self._boundary not in self._buf:
            return
        start = self._buf.find(self._boundary)
        while start >= 0:
            next_start = self._buf.find(self._boundary, start + len(self._boundary))
            if next_start < 0:
                break
            chunk = self._buf[start:next_start]
            hdr_end = chunk.find(b"\r\n\r\n")
            if hdr_end >= 0:
                jpeg_start = hdr_end + 4
                jpeg_data = chunk[jpeg_start:]
                if len(jpeg_data) > 100:
                    img = cv2.imdecode(np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_COLOR)
                    if img is not None:
                        with self._lock:
                            self._frame = img
            start = next_start
        self._buf = self._buf[start:] if start >= 0 else self._buf[-len(self._boundary) * 2:]

    def read(self):
        for _ in range(200):
            with self._lock:
                if self._frame is not None:
                    return True, self._frame.copy()
            time.sleep(0.01)
        return False, None

    def isOpened(self):
        return self._running

    def release(self):
        self._running = False
        if self._stream:
            self._stream.close()

    def get(self, _prop):
        return 0

    def set(self, _prop, _val):
        pass
