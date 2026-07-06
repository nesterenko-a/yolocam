import runtime_settings
import socket
import threading
import time
from pathlib import Path
from urllib.parse import unquote

import cv2
import settings
from notifiers import send_email_archive, send_telegram_archive

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
</script>
</head>
<body>
<div class="row">
<h2>Settings</h2>
<label>Camera URL:<br>
<input type="text" value="{camera_url}" onchange="setv('camera_url',this.value)"></label>
<label><input type="checkbox" {video_enabled} onchange="setv('video_enabled',this.checked)"> Record video</label>
<label><input type="checkbox" {send_video_email} onchange="setv('send_video_email',this.checked)"> Send video via Email</label>
<label><input type="checkbox" {send_video_telegram} onchange="setv('send_video_telegram',this.checked)"> Send video via Telegram</label>
<label><input type="checkbox" {face_enabled} onchange="setv('face_enabled',this.checked)"> Face recognition</label>
<label>Detection mode:<br>
<select onchange="setv('mode_index',this.value)">
<option value="0" {mode0}>People</option>
<option value="1" {mode1}>Animals</option>
<option value="2" {mode2}>Objects</option>
<option value="3" {mode3}>All</option>
</select></label>
<h3>Telegram</h3>
<label>Bot Token:<br>
<input type="text" value="{telegram_token}" onchange="setv('telegram_token',this.value)"></label>
<label>Chat ID:<br>
<input type="text" value="{telegram_chat_id}" onchange="setv('telegram_chat_id',this.value)"></label>
<h3>Email (Gmail)</h3>
<label>From:<br>
<input type="text" value="{email_from}" onchange="setv('email_from',this.value)"></label>
<label>Password:<br>
<input type="text" value="{email_password}" onchange="setv('email_password',this.value)"></label>
<label>To:<br>
<input type="text" value="{email_to}" onchange="setv('email_to',this.value)"></label>
<div style="text-align:center;margin-top:16px">
<a class="btn" href="/" style="background:#336">Back to stream</a>
<a class="btn" href="/archives" style="background:#363">Archives</a>
<a class="btn" href="#" onclick="if(confirm('Delete all archives, videos and snapshots?')){var x=new XMLHttpRequest();x.open('GET','/clear',true);x.onload=function(){alert('Cleared')};x.send()}return false" style="background:#633">Clear data</a>
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
    _CFG.set("mode_index", n)


def is_face_active():
    with _state_lock:
        return _face_active


def toggle_face():
    global _face_active
    with _state_lock:
        _face_active = not _face_active
        _CFG.set("face_enabled", _face_active)
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
.on { background:#0a0; border-color:#0f0; }
.off { background:#600; border-color:#f00; }
</style>
<script>
function cmd(url) {
  var x = new XMLHttpRequest();
  x.open('GET', url, true);
  x.send();
}
function toggle(url,id) {
  var x = new XMLHttpRequest();
  x.open('GET', url, true);
  x.onload = function(){ location.reload(); };
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
<br>
{email_btn}
{telegram_btn}
{policy_btn}
<br>
<a class="btn" href="/settings">Settings</a>
</div>
<img src="/stream">
</body>
</html>"""


def _serve_page(client):
    def state(key, label):
        on = _CFG.get(key)
        cls = "btn on" if on else "btn off"
        val = "0" if on else "1"
        return f'<a class="{cls}" href="#" onclick="toggle(\'/settings/set?{key}={val}\',\'{key}\');return false">{label}: {"ON" if on else "OFF"}</a>'
    page = HTML
    page = page.replace("{email_btn}", state("send_email", "Email"))
    page = page.replace("{telegram_btn}", state("send_telegram", "Telegram"))
    page = page.replace("{policy_btn}", state("policy_alert", "Alert UNKNOWN"))
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n" + page.encode())
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
    def sel(n):
        return "selected" if cfg.get("mode_index") == n else ""
    html = SETTINGS_HTML
    html = html.replace("{camera_url}", cfg.get("camera_url", ""))
    html = html.replace("{face_enabled}", chk("face_enabled"))
    html = html.replace("{mode0}", sel(0))
    html = html.replace("{mode1}", sel(1))
    html = html.replace("{mode2}", sel(2))
    html = html.replace("{mode3}", sel(3))
    html = html.replace("{video_enabled}", chk("video_enabled"))
    html = html.replace("{send_video_email}", chk("send_video_email"))
    html = html.replace("{send_video_telegram}", chk("send_video_telegram"))
    html = html.replace("{telegram_token}", cfg.get("telegram_token", ""))
    html = html.replace("{telegram_chat_id}", cfg.get("telegram_chat_id", ""))
    html = html.replace("{email_from}", cfg.get("email_from", ""))
    html = html.replace("{email_password}", cfg.get("email_password", ""))
    html = html.replace("{email_to}", cfg.get("email_to", ""))
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


ARCHIVES_HTML = """\
<html>
<head>
<meta charset="utf-8">
<title>YOLO Archives</title>
<style>
body { margin:20px; background:#111; color:#fff; font:16px sans-serif; text-align:center; }
table { margin:auto; border-collapse:collapse; }
td, th { padding:8px 12px; border:1px solid #555; }
.btn { display:inline-block; margin:6px 4px; padding:8px 20px; background:#333; color:#fff;
       border:1px solid #555; border-radius:4px; cursor:pointer; font-size:14px; }
.btn:hover { background:#555; }
</style>
<script>
function toggle_all(s) {
  var c = document.getElementsByName('file');
  for(var i=0;i<c.length;i++) c[i].checked=s.checked;
}
function send_selected() {
  var c = document.getElementsByName('file');
  var ids = [];
  for(var i=0;i<c.length;i++) if(c[i].checked) ids.push(c[i].value);
  if(ids.length==0){alert('Select files');return}
  var x = new XMLHttpRequest();
  x.open('POST', '/archives/send', true);
  x.setRequestHeader('Content-Type','application/x-www-form-urlencoded');
  x.onload = function(){ location.reload(); };
  x.send('files='+ids.join(','));
}
</script>
</head>
<body>
<h2>Archives</h2>
<table>
<tr><th><input type=checkbox onchange='toggle_all(this)'></th><th>File</th><th>Size</th></tr>
{rows}
</table>
<div style="margin-top:16px">
<a class="btn" href="#" onclick="send_selected();return false">Send selected</a>
<a class="btn" href="/settings" style="background:#336">Back</a>
</div>
</body>
</html>"""


def _serve_archives(client):
    rows = ""
    for d in [settings.ARCHIVE_DIR, settings.VIDEO_DIR, settings.SAVE_DIR]:
        for f in sorted(d.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.is_file():
                sz = f.stat().st_size
                label = f"{f.parent.name}/{f.name}"
                rows += f"<tr><td><input type=checkbox name=file value='{f}'></td><td>{label}</td><td>{sz/1024:.0f} KB</td></tr>"
    if not rows:
        rows = "<tr><td colspan=3>No files</td></tr>"
    page = ARCHIVES_HTML.replace("{rows}", rows)
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n" + page.encode())
    except Exception:
        pass
    client.close()


def _serve_archives_send(client, body):
    try:
        files_str = body.split("files=")[-1].split("&")[0]
        files_str = unquote(files_str)
        paths = [Path(p) for p in files_str.split(",") if p]
        for p in paths:
            if p.exists():
                send_email_archive(p, settings)
                send_telegram_archive(p, settings)
                p.unlink()
    except Exception as e:
        print(f"Send archives error: {e}")
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nOK")
    except Exception:
        pass
    client.close()


def _serve_clear(client):
    for d in [settings.ARCHIVE_DIR, settings.VIDEO_DIR, settings.SAVE_DIR]:
        for f in d.glob("*"):
            if f.is_file():
                f.unlink()
    try:
        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nCleared")
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
    elif "GET /clear" in line:
        _serve_clear(client)
    elif "GET /archives/send" in line or "POST /archives/send" in line:
        body = data.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in data else ""
        _serve_archives_send(client, body)
    elif "GET /archives" in line:
        _serve_archives(client)
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
