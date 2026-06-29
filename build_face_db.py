import pickle
from pathlib import Path

import cv2

import settings
from employee_faces import normalize

try:
    from insightface.app import FaceAnalysis
except ImportError as exc:
    raise SystemExit("InsightFace is not installed. Run: pip install -r requirements.txt") from exc


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    dataset_dir = Path(settings.DATASET_DIR)
    if not dataset_dir.exists():
        raise SystemExit(f"Dataset directory not found: {dataset_dir}")

    app = FaceAnalysis(
        name="buffalo_l",
        providers=["CPUExecutionProvider"],
    )
    app.prepare(ctx_id=-1, det_size=settings.FACE_DETECTION_SIZE)

    records = []
    skipped = []

    for person_dir in sorted(path for path in dataset_dir.iterdir() if path.is_dir()):
        image_paths = [
            path for path in sorted(person_dir.iterdir())
            if path.suffix.lower() in IMAGE_EXTENSIONS
        ]

        for image_path in image_paths:
            image = cv2.imread(str(image_path))
            if image is None:
                skipped.append((image_path, "cannot read image"))
                continue

            faces = app.get(image)
            if not faces:
                skipped.append((image_path, "no face found"))
                continue

            face = max(faces, key=lambda item: face_area(item.bbox))
            records.append(
                {
                    "name": person_dir.name,
                    "image": str(image_path),
                    "embedding": normalize(face.embedding),
                }
            )

    settings.FACE_DB_PATH.parent.mkdir(exist_ok=True)
    with open(settings.FACE_DB_PATH, "wb") as file:
        pickle.dump(records, file)

    print(f"Saved {len(records)} face embeddings to {settings.FACE_DB_PATH}")
    if skipped:
        print("Skipped images:")
        for image_path, reason in skipped:
            print(f"- {image_path}: {reason}")


def face_area(box):
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


if __name__ == "__main__":
    main()
