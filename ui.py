import cv2

def setup_window(name, fullscreen):
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)

    if fullscreen:
        cv2.setWindowProperty(name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

def draw_status(frame, mode):
    text = f"Mode: {mode} | 1 people | 2 animals | 3 objects | 4 all | Esc exit"
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 36), (20, 20, 20), -1)
    cv2.putText(frame, text, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)