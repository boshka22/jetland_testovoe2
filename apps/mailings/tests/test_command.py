"""Тесты management-команды import_mailings."""

from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.mailings.models import ImportBatch

from .conftest import make_xlsx


def _row(external_id: str, user_id: int = 1) -> dict:
    return {
        "external_id": external_id,
        "user_id": user_id,
        "email": f"{external_id}@example.com",
        "subject": "Тема",
        "message": "Сообщение",
    }


@pytest.mark.django_db
class TestImportMailingsCommand:
    """Тесты management-команды import_mailings."""

    @patch("apps.mailings.services.send_email")
    def test_successful_import_creates_batch(self, mock_send):
        path = make_xlsx([_row("CMD-1"), _row("CMD-2")])
        call_command("import_mailings", str(path))

        assert ImportBatch.objects.filter(file_path=str(path)).exists()

    @patch("apps.mailings.services.send_email")
    def test_output_contains_counters(self, mock_send, capsys):
        path = make_xlsx([_row("OUT-1"), _row("OUT-2")])
        call_command("import_mailings", str(path))

        out = capsys.readouterr().out
        assert "Обработано строк" in out
        assert "Создано" in out
        assert "Пропущено" in out
        assert "Ошибок" in out

    def test_missing_file_raises_command_error(self):
        with pytest.raises(CommandError, match="not found"):
            call_command("import_mailings", "/nonexistent/file.xlsx")

    @patch("apps.mailings.services.send_email")
    def test_duplicate_rows_reported_as_skipped(self, mock_send, capsys):
        path = make_xlsx([_row("DUP-CMD-1")])
        call_command("import_mailings", str(path))
        call_command("import_mailings", str(path))

        out = capsys.readouterr().out
        assert "1" in out

    def test_invalid_xlsx_raises_command_error(self, tmp_path):
        bad_file = tmp_path / "bad.xlsx"
        bad_file.write_bytes(b"this is not xlsx")
        with pytest.raises(CommandError):
            call_command("import_mailings", str(bad_file))
