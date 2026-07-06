import cv2

def setup_window(name, fullscreen, always_on_top=False):
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)

    if fullscreen:
        cv2.setWindowProperty(name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    if always_on_top:
        cv2.setWindowProperty(name, cv2.WND_PROP_TOPMOST, 1)

def draw_status(frame, mode, face_recognition_active=True):
    h, w = frame.shape[:2]
    scale = max(0.35, min(0.9, w / 1280 * 0.75))
    thickness = max(1, round(scale * 3))
    bar_height = max(24, round(h / 720 * 36))

    face_label = "ON" if face_recognition_active else "OFF"
    text = f"Mode: {mode} | 1 people | 2 animals | 3 objects | 4 all | 5 face:{face_label} | 6 settings | Esc exit"

    cv2.rectangle(frame, (0, 0), (w, bar_height), (20, 20, 20), -1)
    cv2.putText(frame, text, (12, bar_height - 8), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), thickness)