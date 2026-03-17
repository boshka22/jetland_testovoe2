from django.db import models


class ImportBatch(models.Model):
    """Один запуск команды import_mailings.

    Хранит путь к обработанному файлу и итоговые счётчики
    для аудита прошлых импортов.
    """

    file_path = models.CharField(max_length=1024)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total = models.PositiveIntegerField(default=0)
    created = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Import Batch"
        verbose_name_plural = "Import Batches"

    def __str__(self) -> str:
        return f"Batch #{self.pk} — {self.file_path}"


class MailingStatus(models.TextChoices):
    PENDING = "pending", "Ожидает"
    SENT = "sent", "Отправлено"
    FAILED = "failed", "Ошибка"


class MailingRecord(models.Model):
    """Одна запись рассылки, импортированная из XLSX-файла.

    ``external_id`` глобально уникален и используется для предотвращения
    повторной обработки той же строки при повторном импорте файла.
    """

    batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name="records",
    )
    external_id = models.CharField(max_length=255, unique=True, db_index=True)
    user_id = models.PositiveIntegerField()
    email = models.EmailField()
    subject = models.CharField(max_length=998)  # лимит темы по RFC 2822
    message = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=MailingStatus.choices,
        default=MailingStatus.PENDING,
    )
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mailing Record"
        verbose_name_plural = "Mailing Records"

    def __str__(self) -> str:
        return f"MailingRecord {self.external_id} → {self.email} [{self.status}]"
