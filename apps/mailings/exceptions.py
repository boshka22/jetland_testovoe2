"""Доменные исключения пайплайна импорта рассылок."""


class MailingImportError(Exception):
    """Базовое исключение для ошибок импорта, прерывающих команду."""


class FileNotFoundError(MailingImportError):  # noqa: A001
    def __init__(self, path: str) -> None:
        super().__init__(f"File not found: {path}")


class InvalidFileFormatError(MailingImportError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid file format: {reason}")


class RowValidationError(Exception):
    """Выбрасывается для одной некорректной строки; импорт продолжается со следующей."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
