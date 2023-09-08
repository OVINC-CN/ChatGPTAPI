import datetime

from django.contrib import admin
from django.utils.translation import gettext_lazy
from rest_framework.settings import api_settings

from apps.chat.models import ChatLog, ModelPermission


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "model",
        "prompt_tokens",
        "completion_tokens",
        "total_price",
        "created_at_formatted",
        "duration",
    ]
    list_filter = ["model"]
    search_fields = ["user"]

    @admin.display(description=gettext_lazy("Total Price"))
    def total_price(self, log: ChatLog) -> str:
        return "%.6f" % (
            log.prompt_tokens * log.prompt_token_unit_price / 1000
            + log.completion_tokens * log.completion_token_unit_price / 1000
        )

    @admin.display(description=gettext_lazy("Duration(ms)"))
    def duration(self, log: ChatLog) -> int:
        if log.finished_at and log.created_at:
            return log.finished_at - log.created_at
        return -1

    @admin.display(description=gettext_lazy("Create Time"))
    def created_at_formatted(self, log: ChatLog) -> str:
        return datetime.datetime.fromtimestamp(log.created_at / 1000).strftime(api_settings.DATETIME_FORMAT)


@admin.register(ModelPermission)
class ModelPermissionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "model", "expired_at", "created_at"]
    list_filter = ["model"]
    search_fields = ["user"]
