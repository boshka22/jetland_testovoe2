"""Management-команда: импорт рассылок из XLSX-файла."""

import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.mailings.exceptions import MailingImportError
from apps.mailings.services import MailingImportService


class Command(BaseCommand):
    help = "Импортирует рассылки из XLSX-файла и отправляет каждое письмо."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "file",
            type=str,
            help="Путь к XLSX-файлу для импорта.",
        )

    def handle(self, *args, **options) -> None:
        file_path = Path(options["file"])
        service = MailingImportService()

        self.stdout.write(f"Importing: {file_path}")
        started = time.monotonic()

        try:
            result = service.import_file(file_path)
        except MailingImportError as exc:
            raise CommandError(str(exc)) from exc

        elapsed = time.monotonic() - started
        minutes, seconds = divmod(int(elapsed), 60)
        duration = f"{minutes}м {seconds}с" if minutes else f"{seconds}с"

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Импорт завершён: {file_path}"))
        self.stdout.write("─" * 40)
        self.stdout.write(f"{'Обработано строк:':<25} {result.total}")
        self.stdout.write(self.style.SUCCESS(f"{'Создано:':<25} {result.created}"))
        self.stdout.write(f"{'Пропущено (дубли):':<25} {result.skipped}")

        if result.failed:
            self.stdout.write(self.style.ERROR(f"{'Ошибок:':<25} {result.failed}"))
        else:
            self.stdout.write(f"{'Ошибок:':<25} {result.failed}")

        self.stdout.write(f"{'Время:':<25} {duration}")
        self.stdout.write(f"{'Batch ID:':<25} {result.batch_id}")
