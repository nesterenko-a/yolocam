import time
from archive_utils import create_archive
from notifiers import send_email_archive, send_telegram_archive


def delete_files(files):
    for file_path in files:
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass


class Reporter:
    def __init__(self, save_dir, archive_dir, settings):
        self.save_dir = save_dir
        self.archive_dir = archive_dir
        self.settings = settings
        self.sent_files = set()
        self.last_report = time.time()

    def tick(self):
        now = time.time()

        if now - self.last_report < self.settings.REPORT_EVERY_SECONDS:
            return None

        files = sorted(self.save_dir.glob("*.jpg"))
        new_files = [file for file in files if file not in self.sent_files]

        archive_path = create_archive(new_files, self.archive_dir)

        if archive_path:
            if self.settings.SEND_EMAIL:
                send_email_archive(archive_path, self.settings)

            if self.settings.SEND_TELEGRAM:
                send_telegram_archive(archive_path, self.settings)

            self.sent_files.update(new_files)
            delete_files(new_files)

        self.last_report = now
        return archive_path