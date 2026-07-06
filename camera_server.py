"""
Транслирует USB-камеру по HTTP (MJPEG).
Основная программа подключается через YOLO_CAMERA=http://localhost:PORT/stream

Использование:
    python camera_server.py                    # порт 8081, камера 0
    python camera_server.py --index 1 --port 9090
"""

import argparse
import socket
import threading
import time

import cv2


def _get_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        ips.append(socket.gethostbyname(hostname))
    except Exception:
        pass
    for info in socket.getaddrinfo(hostname, None):
        ip = info[4][0]
        if ip not in ips and not ip.startswith("127."):
            ips.append(ip)
    return ips


class CameraServer:
    def __init__(self, camera_index, port):
        self.camera_index = camera_index
        self.port = port
        self._frame = None
        self._lock = threading.Lock()

    def _capture(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"Camera {self.camera_index} not found")
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        while True:
            ok, f = cap.read()
            if ok:
                with self._lock:
                    self._frame = f
            time.sleep(1 / 30)

    def _handle(self, client):
        try:
            data = client.recv(4096).decode("utf-8", errors="replace")
        except Exception:
            client.close()
            return

        if "GET /stream" not in data:
            body = b"<html><body><img src='/stream' style='max-width:100%'></body></html>"
            try:
                client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n" + body)
            except Exception:
                pass
            client.close()
            return

        boundary = b"--FRAME"
        try:
            client.sendall(
                b"HTTP/1.0 200 OK\r\n"
                b"Content-Type: multipart/x-mixed-replace; boundary=FRAME\r\n"
                b"Cache-Control: no-cache\r\n\r\n"
            )
            while True:
                with self._lock:
                    f = self._frame
                if f is None:
                    time.sleep(0.1)
                    continue
                ret, jpeg = cv2.imencode(".jpg", f, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if not ret:
                    continue
                try:
                    client.sendall(boundary + b"\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    break
                time.sleep(1 / 30)
        except Exception:
            pass
        finally:
            client.close()

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", self.port))
        server.listen(5)
        print(f"Camera stream: http://localhost:{self.port}/stream")
        for ip in _get_ips():
            print(f"               http://{ip}:{self.port}/stream")
        print(f"Set YOLO_CAMERA=http://<IP>:{self.port}/stream in main app or docker-compose")

        threading.Thread(target=self._capture, daemon=True).start()

        while True:
            client, _ = server.accept()
            threading.Thread(target=self._handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="USB camera → HTTP MJPEG stream")
    parser.add_argument("--index", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--port", type=int, default=8081, help="Stream port (default: 8081)")
    args = parser.parse_args()
    CameraServer(args.index, args.port).run()
