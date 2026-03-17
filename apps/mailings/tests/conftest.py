"""Фабрики и фикстуры для тестов рассылок."""

from pathlib import Path

import factory
import openpyxl

from apps.mailings.models import ImportBatch, MailingRecord


class ImportBatchFactory(factory.django.DjangoModelFactory):
    file_path = factory.Sequence(lambda n: f"/tmp/batch_{n}.xlsx")

    class Meta:
        model = ImportBatch


class MailingRecordFactory(factory.django.DjangoModelFactory):
    batch = factory.SubFactory(ImportBatchFactory)
    external_id = factory.Sequence(lambda n: f"EXT-{n:04d}")
    user_id = factory.Sequence(lambda n: n + 1)
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    subject = "Тестовая тема"
    message = "Тестовый текст письма"

    class Meta:
        model = MailingRecord


def make_xlsx(rows: list[dict], columns: list[str] | None = None) -> Path:
    """Создаёт временный XLSX-файл и возвращает его путь.

    Args:
        rows: Список словарей с данными рассылки.
        columns: Порядок колонок; по умолчанию — стандартный набор.

    Returns:
        Путь к созданному XLSX-файлу.
    """
    cols = columns or ["external_id", "user_id", "email", "subject", "message"]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(cols)
    for row in rows:
        ws.append([row.get(c) for c in cols])

    path = Path(f"/tmp/test_import_{id(rows)}.xlsx")
    wb.save(path)
    return path
