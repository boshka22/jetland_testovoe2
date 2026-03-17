"""Юнит- и интеграционные тесты сервиса импорта рассылок."""

from pathlib import Path
from unittest.mock import patch

import pytest

from apps.mailings.exceptions import (
    FileNotFoundError as MailingFileNotFoundError,
)
from apps.mailings.exceptions import (
    InvalidFileFormatError,
    RowValidationError,
)
from apps.mailings.models import MailingRecord, MailingStatus
from apps.mailings.services import (
    MailingImportService,
    iter_xlsx_rows,
    validate_row,
)

from .conftest import make_xlsx

# ---------------------------------------------------------------------------
# validate_row
# ---------------------------------------------------------------------------


class TestValidateRow:
    """Юнит-тесты функции валидации строки."""

    def _valid(self, **overrides) -> dict:
        base = {
            "external_id": "EXT-001",
            "user_id": 42,
            "email": "user@example.com",
            "subject": "Привет",
            "message": "Текст письма",
        }
        return {**base, **overrides}

    def test_valid_row_passes(self):
        result = validate_row(self._valid())
        assert result["external_id"] == "EXT-001"
        assert result["user_id"] == 42

    def test_user_id_cast_to_int(self):
        result = validate_row(self._valid(user_id="7"))
        assert result["user_id"] == 7

    def test_empty_external_id_raises(self):
        with pytest.raises(RowValidationError, match="external_id"):
            validate_row(self._valid(external_id=""))

    def test_none_external_id_raises(self):
        with pytest.raises(RowValidationError, match="external_id"):
            validate_row(self._valid(external_id=None))

    def test_invalid_user_id_raises(self):
        with pytest.raises(RowValidationError, match="user_id"):
            validate_row(self._valid(user_id="not-a-number"))

    def test_zero_user_id_raises(self):
        with pytest.raises(RowValidationError, match="user_id"):
            validate_row(self._valid(user_id=0))

    def test_invalid_email_raises(self):
        with pytest.raises(RowValidationError, match="email"):
            validate_row(self._valid(email="not-an-email"))

    def test_empty_subject_raises(self):
        with pytest.raises(RowValidationError, match="subject"):
            validate_row(self._valid(subject=""))

    def test_empty_message_raises(self):
        with pytest.raises(RowValidationError, match="message"):
            validate_row(self._valid(message=None))


# ---------------------------------------------------------------------------
# iter_xlsx_rows
# ---------------------------------------------------------------------------


class TestIterXlsxRows:
    """Тесты генератора чтения XLSX."""

    def test_yields_correct_rows(self):
        path = make_xlsx(
            [
                {
                    "external_id": "A1",
                    "user_id": 1,
                    "email": "a@b.com",
                    "subject": "S",
                    "message": "M",
                },
            ]
        )
        rows = list(iter_xlsx_rows(path))
        assert len(rows) == 1
        assert rows[0]["external_id"] == "A1"

    def test_yields_multiple_rows(self):
        data = [
            {
                "external_id": f"ID-{i}",
                "user_id": i,
                "email": f"u{i}@x.com",
                "subject": "S",
                "message": "M",
            }
            for i in range(1, 6)
        ]
        rows = list(iter_xlsx_rows(make_xlsx(data)))
        assert len(rows) == 5

    def test_missing_file_raises(self):
        with pytest.raises(MailingFileNotFoundError):
            list(iter_xlsx_rows(Path("/nonexistent/file.xlsx")))

    def test_missing_column_raises(self):
        path = make_xlsx(
            [{"external_id": "X", "user_id": 1}],
            columns=["external_id", "user_id"],
        )
        with pytest.raises(InvalidFileFormatError, match="Отсутствуют обязательные колонки"):
            list(iter_xlsx_rows(path))

    def test_empty_file_raises(self):
        """Файл без строк (даже без заголовка) вызывает InvalidFileFormatError."""
        import openpyxl

        wb = openpyxl.Workbook()
        path = Path("/tmp/empty_test.xlsx")
        wb.save(path)

        with pytest.raises(InvalidFileFormatError, match="пустой"):
            list(iter_xlsx_rows(path))


# ---------------------------------------------------------------------------
# MailingImportService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMailingImportService:
    """Интеграционные тесты полного цикла импорта."""

    def setup_method(self):
        self.service = MailingImportService()

    def _row(self, external_id="EXT-1", user_id=1) -> dict:
        return {
            "external_id": external_id,
            "user_id": user_id,
            "email": "test@example.com",
            "subject": "Привет",
            "message": "Текст",
        }

    @patch("apps.mailings.services.send_email")
    def test_creates_record_and_marks_sent(self, mock_send):
        path = make_xlsx([self._row()])
        result = self.service.import_file(path)

        assert result.total == 1
        assert result.created == 1
        assert result.skipped == 0
        assert result.failed == 0
        mock_send.assert_called_once()

    @patch("apps.mailings.services.send_email")
    def test_skips_duplicate_external_id(self, mock_send):
        path = make_xlsx([self._row("DUP-1")])
        self.service.import_file(path)

        result = self.service.import_file(path)
        assert result.skipped == 1
        assert result.created == 0
        assert mock_send.call_count == 1

    @patch("apps.mailings.services.send_email")
    def test_failed_row_does_not_stop_import(self, mock_send):
        rows = [
            self._row("GOOD-1", user_id=1),
            {**self._row("BAD-1"), "email": "not-valid"},
            self._row("GOOD-2", user_id=2),
        ]
        result = self.service.import_file(make_xlsx(rows))

        assert result.total == 3
        assert result.created == 2
        assert result.failed == 1
        assert mock_send.call_count == 2

    @patch("apps.mailings.services.send_email", side_effect=RuntimeError("SMTP error"))
    def test_send_failure_marks_record_failed(self, mock_send):
        path = make_xlsx([self._row("FAIL-1")])
        result = self.service.import_file(path)

        assert result.failed == 1
        assert result.created == 0
        record = MailingRecord.objects.get(external_id="FAIL-1")
        assert record.status == MailingStatus.FAILED
        assert "SMTP error" in record.error

    @patch("apps.mailings.services.send_email")
    def test_batch_record_created_with_correct_counters(self, mock_send):
        rows = [self._row(f"B-{i}", i) for i in range(1, 4)]
        result = self.service.import_file(make_xlsx(rows))

        from apps.mailings.models import ImportBatch

        batch = ImportBatch.objects.get(pk=result.batch_id)
        assert batch.total == 3
        assert batch.created == 3
        assert batch.finished_at is not None

    def test_missing_file_raises(self):
        with pytest.raises(MailingFileNotFoundError):
            self.service.import_file(Path("/no/such/file.xlsx"))
