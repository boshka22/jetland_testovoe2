from django.contrib import admin

from .models import ImportBatch, MailingRecord


class MailingRecordInline(admin.TabularInline):
    model = MailingRecord
    extra = 0
    readonly_fields = (
        "external_id",
        "user_id",
        "email",
        "subject",
        "status",
        "error",
        "created_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "file_path",
        "started_at",
        "finished_at",
        "total",
        "created",
        "skipped",
        "failed",
    )
    readonly_fields = (
        "file_path",
        "started_at",
        "finished_at",
        "total",
        "created",
        "skipped",
        "failed",
    )
    inlines = [MailingRecordInline]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


@admin.register(MailingRecord)
class MailingRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "external_id",
        "user_id",
        "email",
        "subject",
        "status",
        "created_at",
    )
    list_filter = ("status", "batch")
    search_fields = ("external_id", "email", "user_id")
    readonly_fields = (
        "batch",
        "external_id",
        "user_id",
        "email",
        "subject",
        "message",
        "status",
        "error",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
