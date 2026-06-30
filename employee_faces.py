from __future__ import annotations

import pickle
import warnings
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

warnings.filterwarnings("ignore", message=".*`estimate` is deprecated.*")
try:
    from insightface.app import FaceAnalysis
except ImportError:
    FaceAnalysis = None


@dataclass
class FaceMatch:
    name: str
    similarity: float
    person_box: tuple[int, int, int, int]
    face_box: tuple[int, int, int, int] | None


class EmployeeFaceRecognizer:
    def __init__(
        self,
        db_path,
        threshold,
        det_size=(640, 640),
        providers=None,
    ):
        if FaceAnalysis is None:
            raise RuntimeError(
                "InsightFace is not installed. Run: pip install -r requirements.txt"
            )

        self.db_path = Path(db_path)
        self.threshold = threshold
        self.records = self._load_records()
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=providers or ["CPUExecutionProvider"],
        )
        self.app.prepare(ctx_id=-1, det_size=det_size)

    def _load_records(self):
        if not self.db_path.exists():
            return []

        with open(self.db_path, "rb") as file:
            records = pickle.load(file)

        for record in records:
            record["embedding"] = normalize(record["embedding"])

        return records

    def identify_people(self, frame, result, min_person_confidence):
        matches = []

        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            if class_id != 0 or confidence < min_person_confidence:
                continue

            person_box = clamp_box(box.xyxy[0].tolist(), frame.shape)
            match = self.identify_person(frame, person_box)
            matches.append(match)

        return matches

    def identify_person(self, frame, person_box):
        x1, y1, x2, y2 = person_box
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return FaceMatch("UNKNOWN", 0.0, person_box, None)

        faces = self.app.get(crop)
        if not faces:
            return FaceMatch("NO_FACE", 0.0, person_box, None)

        face = max(faces, key=lambda item: face_area(item.bbox))
        embedding = normalize(face.embedding)
        name, similarity = self._best_match(embedding)
        label = name if similarity >= self.threshold else "UNKNOWN"
        fx1, fy1, fx2, fy2 = clamp_box(face.bbox.tolist(), crop.shape)
        face_box = (x1 + fx1, y1 + fy1, x1 + fx2, y1 + fy2)

        return FaceMatch(label, similarity, person_box, face_box)

    def _best_match(self, embedding):
        if not self.records:
            return "UNKNOWN", 0.0

        best_name = "UNKNOWN"
        best_similarity = -1.0

        for record in self.records:
            similarity = float(np.dot(embedding, record["embedding"]))
            if similarity > best_similarity:
                best_name = record["name"]
                best_similarity = similarity

        return best_name, best_similarity


def normalize(embedding):
    embedding = np.asarray(embedding, dtype=np.float32)
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm


def clamp_box(box, shape):
    height, width = shape[:2]
    x1, y1, x2, y2 = [int(round(value)) for value in box]
    x1 = max(0, min(width - 1, x1))
    y1 = max(0, min(height - 1, y1))
    x2 = max(0, min(width, x2))
    y2 = max(0, min(height, y2))
    return x1, y1, x2, y2


def face_area(box):
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def draw_face_matches(frame, matches):
    for match in matches:
        x1, y1, x2, y2 = match.person_box
        known = match.name not in ("UNKNOWN", "NO_FACE")
        color = (0, 180, 0) if known else (0, 0, 255)
        label = format_match_label(match)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        draw_label(frame, label, x1, max(0, y1 - 8), color)

        if match.face_box:
            fx1, fy1, fx2, fy2 = match.face_box
            cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), color, 1)


def draw_detection_labels(frame, result, face_matches):
    face_matches_by_box = {match.person_box: match for match in face_matches}

    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        detection_box = clamp_box(box.xyxy[0].tolist(), frame.shape)
        class_name = get_class_name(result.names, class_id)
        label = f"{class_name} {confidence:.2f}"
        color = (0, 180, 0) if class_id == 0 else (255, 120, 0)

        face_match = face_matches_by_box.get(detection_box)
        if face_match:
            label = f"{label} | {format_match_label(face_match)}"
            if face_match.name in ("UNKNOWN", "NO_FACE"):
                color = (0, 0, 255)

            if face_match.face_box:
                fx1, fy1, fx2, fy2 = face_match.face_box
                cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), color, 1)

        x1, y1, _, _ = detection_box
        draw_label(frame, label, x1, max(0, y1 - 8), color)


def draw_face_labels(frame, matches):
    for match in matches:
        if match.similarity <= 0:
            continue

        x1, y1, _, _ = match.person_box
        known = match.name not in ("UNKNOWN", "NO_FACE")
        color = (0, 180, 0) if known else (0, 0, 255)
        draw_label(frame, format_match_label(match), x1, max(0, y1 - 8), color)


def get_class_name(names, class_id):
    if hasattr(names, "get"):
        return names.get(class_id, str(class_id))

    if 0 <= class_id < len(names):
        return names[class_id]

    return str(class_id)


def format_match_label(match):
    if match.similarity > 0:
        return f"{match.name} {match.similarity:.2f}"
    return match.name


def draw_label(frame, text, x, y, color):
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.7
    thickness = 2
    (text_width, text_height), baseline = cv2.getTextSize(text, font, scale, thickness)
    top = max(0, y - text_height - baseline - 4)
    cv2.rectangle(
        frame,
        (x, top),
        (x + text_width + 8, top + text_height + baseline + 6),
        color,
        -1,
    )
    cv2.putText(
        frame,
        text,
        (x + 4, top + text_height + 2),
        font,
        scale,
        (255, 255, 255),
        thickness,
    )
