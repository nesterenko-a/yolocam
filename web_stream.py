import runtime_settings
import socket
import threading
import time
from urllib.parse import unquote

import cv2

_CFG = runtime_settings

SETTINGS_HTML = """\
<html>
<head>
<meta charset="utf-8">
<title>YOLO Settings</title>
<style>
body { margin:20px; background:#111; color:#fff; font:16px sans-serif; }
label { display:block; margin:10px 0; }
input[type=text] { width:100%; padding:6px; background:#333; color:#fff; border:1px solid #555; border-radius:4px; }
input[type=checkbox] { transform:scale(1.3); margin-right:8px; }
.btn { display:inline-block; margin:6px 4px; padding:8px 20px; background:#333; color:#fff;
       border:1px solid #555; border-radius:4px; cursor:pointer; font-size:14px; }
.btn:hover { background:#555; }
.row { max-width:500px; margin:auto; text-align:left; }
h2 { text-align:center; }
</style>
<script>
function setv(k,v) {
  var x = new XMLHttpRequest();
  x.open('GET', '/settings/set?'+k+'='+encodeURIComponent(v), true);
  x.send();
}
function save() {
  var x = new XMLHttpRequest(); x.open('GET','/settings/save',true); x.send();
  document.getElementById('msg').innerText = 'Saved';
}
function reset() {
  var x = new XMLHttpRequest(); x.open('GET','/settings/reset',true);
  x.onload = function(){ location.reload(); };
  x.send();
}
</script>
</head>
<body>
<div class="row">
<h2>Settings</h2>
<label>Camera URL:<br>
<input type="text" id="cam" value="{camera_url}" onchange="setv('camera_url',this.value)"></label>
<label><input type="checkbox" {send_email} onchange="setv('send_email',this.checked)"> Send Email</label>
<label><input type="checkbox" {send_telegram} onchange="setv('send_telegram',this.checked)"> Send Telegram</label>
<label><input type="checkbox" {video_enabled} onchange="setv('video_enabled',this.checked)"> Record video</label>
<label><input type="checkbox" {send_video_email} onchange="setv('send_video_email',this.checked)"> Send video via Email</label>
<label><input type="checkbox" {send_video_telegram} onchange="setv('send_video_telegram',this.checked)"> Send video via Telegram</label>
<div style="text-align:center;margin-top:16px">
<a class="btn" href="#" onclick="save();return false">Save</a>
<a class="btn" href="#" onclick="reset();return false" style="background:#600">Reset to defaults</a>
<a class="btn" href="/" style="background:#336">Back to stream</a>
</div>
<p id="msg" style="text-align:center;color:#0f0"></p>
</div>
</body>
</html>"""


_current_frame = None
_lock = threading.Lock()

_mode_index = 0
_face_active = True
_state_lock = threading.Lock()


def set_frame(frame):
    global _current_frame
    with _lock:
        _current_frame = frame


def _get_frame():
    with _lock:
        if _current_frame is None:
            return None
        return _current_frame.copy()


def get_mode_index():
    with _state_lock:
        return _mode_index


def set_mode_index(n):
    global _mode_index
    with _state_lock:
        _mode_index = n


def is_face_active():
    with _state_lock:
        return _face_active


def toggle_face():
    global _face_active
    with _state_lock:
        _face_active = not _face_active
        return _face_active


HTML = """\
<html>
<head>
<meta charset="utf-8">
<title>YOLO Stream</title>
<style>
body { margin:0; background:#111; color:#fff; font:16px sans-serif; text-align:center; }
img { max-width:100%; height:auto; }
.controls { padding:10px; }
.btn { display:inline-block; margin:4px; padding:8px 16px; background:#333; color:#fff;
        border:1px solid #555; border-radius:4px; cursor:pointer; font-size:14px; }
.btn:hover { background:#555; }
</style>
<script>
function cmd(url) {
  var x = new XMLHttpRequest();
  x.open('GET', url, true);
  x.send();
}
</script>
</head>
<body>
<div class="controls">
<a class="btn" href="#" onclick="cmd('/mode?n=0');return false">People</a>
<a class="btn" href="#" onclick="cmd('/mode?n=1');return false">Animals</a>
<a class="btn" href="#" onclick="cmd('/mode?n=2');return false">Objects</a>
<a class="btn" href="#" onclick="cmd('/mode?n=3');return false">All</a>
<a class="btn" href="#" onclick="cmd('/face/toggle');return false">Face: ON/OFF</a>
<a class="btn" href="/settings">Settings</a>
</div>
<img src="/stream">
</body>
</html>"""


def _serve_page(client):
    page = HTML.encode()
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n" + page)
    except Exception:
        pass
    client.close()


def _serve_mode(client, path):
    try:
        n = int(path.split("n=")[-1].split()[0])
        if 0 <= n <= 3:
            set_mode_index(n)
    except Exception:
        pass
    body = b"OK"
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\n" + body)
    except Exception:
        pass
    client.close()


def _serve_face(client):
    state = toggle_face()
    body = b"ON" if state else b"OFF"
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\n" + body)
    except Exception:
        pass
    client.close()


def _serve_settings(client):
    cfg = _CFG.all()
    def chk(key):
        return "checked" if cfg.get(key) else ""
    html = SETTINGS_HTML.format(
        camera_url=cfg.get("camera_url", ""),
        send_email=chk("send_email"),
        send_telegram=chk("send_telegram"),
        video_enabled=chk("video_enabled"),
        send_video_email=chk("send_video_email"),
        send_video_telegram=chk("send_video_telegram"),
    )
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n" + html.encode())
    except Exception:
        pass
    client.close()


def _serve_settings_set(client, path):
    try:
        qs = path.split("?", 1)[1].split()[0]
        for pair in qs.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                v = v.replace("+", "%20").replace("%20", " ")
                v = unquote(v)
                if v.lower() in ("true", "on", "1"):
                    _CFG.set(k, True)
                elif v.lower() in ("false", "off", "0"):
                    _CFG.set(k, False)
                else:
                    _CFG.set(k, v)
    except Exception:
        pass
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nOK")
    except Exception:
        pass
    client.close()


def _serve_settings_save(client):
    _CFG.save()
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nSaved")
    except Exception:
        pass
    client.close()


def _serve_settings_reset(client):
    _CFG.reset()
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nReset")
    except Exception:
        pass
    client.close()


def _handle(client):
    try:
        data = client.recv(4096).decode("utf-8", errors="replace")
        line = data.split("\r\n")[0]
    except Exception:
        client.close()
        return

    if "GET /stream" in line:
        _serve_stream(client)
    elif "GET /mode?" in line:
        _serve_mode(client, line)
    elif "GET /face/toggle" in line:
        _serve_face(client)
    elif "GET /settings/save" in line:
        _serve_settings_save(client)
    elif "GET /settings/reset" in line:
        _serve_settings_reset(client)
    elif "GET /settings/set?" in line:
        _serve_settings_set(client, line)
    elif "GET /settings" in line:
        _serve_settings(client)
    else:
        _serve_page(client)


def _serve_stream(client):
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
