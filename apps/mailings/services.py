"""Бизнес-логика импорта рассылок из XLSX-файла."""

import logging
from dataclasses import dataclass
from pathlib import Path

import openpyxl

from apps.mailings.email import send_email
from apps.mailings.exceptions import (
    FileNotFoundError,
    InvalidFileFormatError,
    RowValidationError,
)
from apps.mailings.models import ImportBatch, MailingRecord, MailingStatus

logger = logging.getLogger(__name__)

# Колонки, обязательные в заголовке XLSX-файла.
REQUIRED_COLUMNS = {"external_id", "user_id", "email", "subject", "message"}


@dataclass
class ImportResult:
    """Счётчики, собранные за один запуск импорта."""

    total: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0
    batch_id: int | None = None


# ---------------------------------------------------------------------------
# XLSX reader
# ---------------------------------------------------------------------------


def iter_xlsx_rows(file_path: Path):
    """Построчно читает XLSX-файл, отдавая по одному словарю за раз.

    Использует режим ``read_only`` openpyxl — весь файл никогда не
    загружается в память, что позволяет обрабатывать файлы любого размера.

    Args:
        file_path: Путь к XLSX-файлу.

    Yields:
        Словарь ``заголовок колонки → значение ячейки`` для каждой строки данных.

    Raises:
        FileNotFoundError: Файл не найден.
        InvalidFileFormatError: Файл не является корректным XLSX или в первой
            строке отсутствуют обязательные заголовки.
    """
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))

    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    except Exception as exc:
        raise InvalidFileFormatError(str(exc)) from exc

    ws = wb.active
    rows = ws.iter_rows(values_only=True)

    try:
        header = next(rows)
    except StopIteration as exc:
        wb.close()
        raise InvalidFileFormatError("Файл пустой.") from exc

    columns = [str(c).strip() if c is not None else "" for c in header]
    missing = REQUIRED_COLUMNS - set(columns)
    if missing:
        wb.close()
        raise InvalidFileFormatError(
            f"Отсутствуют обязательные колонки: {', '.join(sorted(missing))}"
        )

    for row in rows:
        yield dict(zip(columns, row, strict=False))

    wb.close()


# ---------------------------------------------------------------------------
# Валидация строки
# ---------------------------------------------------------------------------


def validate_row(raw: dict) -> dict:
    """Валидирует и нормализует одну сырую строку из XLSX-файла.

    Args:
        raw: Словарь ``название колонки → сырое значение ячейки``.

    Returns:
        Очищенная строка с непустыми строковыми полями и ``user_id`` приведённым к ``int``.

    Raises:
        RowValidationError: Любое обязательное поле отсутствует или некорректно.
    """
    cleaned = {}

    for col in ("external_id", "email", "subject", "message"):
        value = str(raw.get(col) or "").strip()
        if not value:
            raise RowValidationError(f"Колонка '{col}' пустая.")
        cleaned[col] = value

    raw_user_id = raw.get("user_id")
    try:
        cleaned["user_id"] = int(raw_user_id)
        if cleaned["user_id"] <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise RowValidationError(
            f"Колонка 'user_id' должна быть положительным целым числом, получено: {raw_user_id!r}"
        ) from None

    if "@" not in cleaned["email"]:
        raise RowValidationError(
            f"Колонка 'email' не похожа на корректный адрес: {cleaned['email']!r}"
        )

    return cleaned


# ---------------------------------------------------------------------------
# Сервис импорта
# ---------------------------------------------------------------------------


class MailingImportService:
    """Оркестрирует чтение, валидацию, сохранение и отправку рассылок.

    Создаёт одну запись ``ImportBatch`` на каждый запуск для аудита.
    """

    def import_file(self, file_path: Path) -> ImportResult:
        """Импортирует все строки рассылок из *file_path*.

        Читает файл построчно (без полной загрузки в память), создаёт
        ``MailingRecord`` для каждой валидной новой строки и вызывает
        ``send_email``. Дублирующиеся ``external_id`` молча пропускаются.
        Строки с ошибками валидации или сбоями отправки помечаются как
        ``FAILED`` и не прерывают импорт.

        Args:
            file_path: Путь к XLSX-файлу.

        Returns:
            :class:`ImportResult` с финальными счётчиками.

        Raises:
            FileNotFoundError: Файл не существует.
            InvalidFileFormatError: Файл не является корректным XLSX или
                отсутствуют обязательные колонки. Импорт немедленно прерывается.
        """
        batch = ImportBatch.objects.create(file_path=str(file_path))
        result = ImportResult(batch_id=batch.pk)

        for raw_row in iter_xlsx_rows(file_path):
            result.total += 1
            self._process_row(raw_row, batch, result)

        self._finalise_batch(batch, result)
        return result

    def _process_row(
        self,
        raw_row: dict,
        batch: ImportBatch,
        result: ImportResult,
    ) -> None:
        """Обрабатывает одну сырую строку из таблицы.

        Обновляет счётчики *result* на месте.
        """
        try:
            row = validate_row(raw_row)
        except RowValidationError as exc:
            logger.warning("Ошибка валидации строки: %s | строка=%r", exc, raw_row)
            result.failed += 1
            return

        if MailingRecord.objects.filter(external_id=row["external_id"]).exists():
            logger.debug("Пропуск дубля external_id=%s", row["external_id"])
            result.skipped += 1
            return

        record = MailingRecord.objects.create(
            batch=batch,
            external_id=row["external_id"],
            user_id=row["user_id"],
            email=row["email"],
            subject=row["subject"],
            message=row["message"],
            status=MailingStatus.PENDING,
        )

        self._send(record)

        if record.status == MailingStatus.SENT:
            result.created += 1
        else:
            result.failed += 1

    @staticmethod
    def _send(record: MailingRecord) -> None:
        """Вызывает send_email и обновляет статус записи."""
        try:
            send_email(
                user_id=record.user_id,
                email=record.email,
                subject=record.subject,
                message=record.message,
            )
            record.status = MailingStatus.SENT
        except Exception as exc:
            logger.error(
                "Ошибка отправки для external_id=%s: %s",
                record.external_id,
                exc,
            )
            record.status = MailingStatus.FAILED
            record.error = str(exc)
        finally:
            record.save(update_fields=["status", "error", "updated_at"])

    @staticmethod
    def _finalise_batch(batch: ImportBatch, result: ImportResult) -> None:
        """Сохраняет финальные счётчики и время завершения в запись батча."""
        from django.utils import timezone

        batch.total = result.total
        batch.created = result.created
        batch.skipped = result.skipped
        batch.failed = result.failed
        batch.finished_at = timezone.now()
        batch.save(update_fields=["total", "created", "skipped", "failed", "finished_at"])
