import datetime

from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy
from rest_framework.settings import api_settings

from apps.chat.models import (
    AIModel,
    ChatLog,
    ChatMessageChangeLog,
    ModelPermission,
    SystemPreset,
)


class UserNicknameMixin:
    @admin.display(description=gettext_lazy("Nick Name"))
    def user__nick_name(self, inst) -> str:
        if inst.user:
            return inst.user.nick_name
        return ""


@admin.register(ChatLog)
class ChatLogAdmin(UserNicknameMixin, admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "user__nick_name",
        "model",
        "model_name",
        "prompt_tokens",
        "completion_tokens",
        "vision_count",
        "total_price",
        "created_at_formatted",
        "duration",
        "is_charged",
    ]
    list_filter = ["model"]
    search_fields = ["user__nick_name", "user__username"]

    @admin.display(description=gettext_lazy("Total Price"))
    def total_price(self, log: ChatLog) -> str:
        price = (
            log.prompt_tokens * log.prompt_token_unit_price / 1000
            + log.completion_tokens * log.completion_token_unit_price / 1000
            + log.vision_count * log.vision_unit_price / 1000
            + log.request_unit_price / 1000
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

    @admin.display(description=gettext_lazy("Model Name"))
    def model_name(self, inst: ChatLog) -> str:
        model_inst: AIModel = AIModel.objects.filter(model=inst.model).first()
        if model_inst is None:
            return "--"
        return model_inst.name


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "icon_display",
        "model",
        "name",
        "is_enabled",
        "prompt_price",
        "completion_price",
        "vision_price",
        "request_price",
        "support_vision",
        "support_system_define",
        "is_public",
    ]
    list_filter = ["provider", "is_enabled", "support_vision", "support_system_define", "is_public"]
    search_fields = ["name"]

    @admin.display(description=gettext_lazy("Icon"))
    def icon_display(self, model: AIModel) -> str:
        return format_html(
            f'<img src="{model.icon if model.icon else f"{settings.FRONTEND_URL}/favicon.ico"}" '
            f'width="18" height="18" />'
        )


@admin.register(SystemPreset)
class SystemPresetAdmin(UserNicknameMixin, admin.ModelAdmin):
    list_display = ["id", "name", "is_public", "user", "user__nick_name", "updated_at", "created_at"]
    search_fields = ["name"]
    list_filter = ["is_public"]


@admin.register(ModelPermission)
class ModelPermissionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "model_names"]
    list_filter = ["models"]
    search_fields = ["user__nick_name", "user__username"]

    @admin.display(description=gettext_lazy("Model Name"))
    def model_names(self, p: ModelPermission) -> str:
        return "; ".join(p.models.all().values_list("name", flat=True))


@admin.register(ChatMessageChangeLog)
class ChatMessageChangeLogAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "message_id", "action", "created_at"]
    list_filter = ["action"]
    search_fields = ["user__nick_name", "user__username"]
    ordering = ["-id"]
