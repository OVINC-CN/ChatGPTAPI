import datetime
from typing import Union

from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy
from rest_framework.settings import api_settings

from apps.chat.models import AIModel, ChatLog, ModelPermission


class ModelNameMixin:
    @admin.display(description=gettext_lazy("Model Name"))
    def model_name(self, inst: Union[ModelPermission, ChatLog]) -> str:
        model_inst: AIModel = AIModel.objects.filter(model=inst.model, is_enabled=True).first()
        if model_inst is None:
            return f"--({inst.model})"
        return f"{model_inst.name}({model_inst.model})"


@admin.register(ChatLog)
class ChatLogAdmin(ModelNameMixin, admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "model_name",
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
        price = (
            log.prompt_tokens * log.prompt_token_unit_price / 1000
            + log.completion_tokens * log.completion_token_unit_price / 1000
        )
        return f"{price:.4f}"

    @admin.display(description=gettext_lazy("Duration(ms)"))
    def duration(self, log: ChatLog) -> int:
        if log.finished_at and log.created_at:
            return log.finished_at - log.created_at
        return -1

    @admin.display(description=gettext_lazy("Create Time"))
    def created_at_formatted(self, log: ChatLog) -> str:
        return (
            datetime.datetime.fromtimestamp(log.created_at / 1000)
            .astimezone(timezone.get_current_timezone())
            .strftime(api_settings.DATETIME_FORMAT)
        )


@admin.register(ModelPermission)
class ModelPermissionAdmin(ModelNameMixin, admin.ModelAdmin):
    list_display = ["id", "user", "model_name", "expired_at", "created_at"]
    list_filter = ["model"]
    search_fields = ["user"]


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ["id", "provider", "model", "name", "is_enabled", "prompt_price", "completion_price"]
    list_filter = ["provider", "is_enabled"]
