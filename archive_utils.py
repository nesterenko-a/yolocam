import time
import zipfile

def create_archive(files, archive_dir):
    if not files:
        return None

    archive_dir.mkdir(exist_ok=True)
    archive_path = archive_dir / time.strftime("snapshots_%Y-%m-%d_%H-%M-%S.zip")

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            archive.write(file_path, arcname=file_path.name)

    return archive_path