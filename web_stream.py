import socket
import threading
import time

import cv2


_current_frame = None
_lock = threading.Lock()


def set_frame(frame):
    global _current_frame
    with _lock:
        _current_frame = frame


def _get_frame():
    with _lock:
        if _current_frame is None:
            return None
        return _current_frame.copy()


def _handle(client):
    try:
        data = client.recv(4096).decode("utf-8", errors="replace")
    except Exception:
        client.close()
        return

    if "GET /stream" not in data:
        body = (
            b"<html><head><title>YOLO Stream</title></head>"
            b"<body><img src='/stream' style='max-width:100%'></body></html>"
        )
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
            b"Cache-Control: no-cache\r\n"
            b"Connection: close\r\n\r\n"
        )
        while True:
            frame = _get_frame()
            if frame is None:
                break
            ret, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if not ret:
                continue
            try:
                client.sendall(boundary + b"\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                break
            time.sleep(1 / 30)
    except Exception:
        pass
    finally:
        client.close()


def start(port):
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", port))
        server.listen(5)
        print(f"Web stream: http://localhost:{port}")
    except OSError as e:
        print(f"Web stream failed on port {port}: {e}")
        return

    def _serve():
        while True:
            try:
                client, _ = server.accept()
                threading.Thread(target=_handle, args=(client,), daemon=True).start()
            except Exception:
                break

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
