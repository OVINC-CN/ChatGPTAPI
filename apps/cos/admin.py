from django.contrib import admin

from apps.cos.models import FileExtractInfo


@admin.register(FileExtractInfo)
class FileExtractInfoAdmin(admin.ModelAdmin):
    list_display = ["id", "file_path", "is_finished", "is_success", "created_at"]
    list_filter = ["is_finished", "is_success"]
    ordering = ["-id"]
