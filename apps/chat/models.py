# pylint: disable=C0103

from decimal import Decimal
from typing import List

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Index, Q, QuerySet
from django.utils.translation import gettext_lazy
from ovinc_client.core.constants import MAX_CHAR_LENGTH, MEDIUM_CHAR_LENGTH
from ovinc_client.core.models import BaseModel, ForeignKey, UniqIDField
from pydantic import BaseModel as BaseDataModel

from apps.chat.constants import (
    PRICE_DECIMAL_NUMS,
    PRICE_DIGIT_NUMS,
    AIModelProvider,
    MessageContentType,
    MessageSyncAction,
    OpenAIRole,
)

USER_MODEL = get_user_model()


class MessageContentImageUrl(BaseDataModel):
    url: str


class MessageContentSource(BaseDataModel):
    type: str
    media_type: str
    data: str


class MessageContent(BaseDataModel):
    type: MessageContentType
    text: str | None = None
    image_url: MessageContentImageUrl | None = None
    source: MessageContentSource | None = None


class Message(BaseDataModel):
    role: OpenAIRole
    content: str | list[MessageContent]
    file: str | None = None


class ChatRequest(BaseDataModel):
    user: str
    model: str
    messages: list[Message]


class HunYuanDelta(BaseDataModel):
    Role: str = ""
    Content: str = ""


class HunYuanChoice(BaseDataModel):
    FinishReason: str = ""
    Delta: HunYuanDelta = None


class HunYuanUsage(BaseDataModel):
    PromptTokens: int = 0
    CompletionTokens: int = 0
    TotalTokens: int = 0


class HunYuanChuck(BaseDataModel):
    Note: str = ""
    Choices: List[HunYuanChoice] | None = None
    Created: int = 0
    Id: str = ""
    Usage: HunYuanUsage | None = None


class OpenRouterModelPrice(BaseDataModel):
    prompt: Decimal
    completion: Decimal
    image: Decimal
    request: Decimal


class OpenRouterModelInfo(BaseDataModel):
    id: str
    pricing: OpenRouterModelPrice


class ChatLog(BaseModel):
    """
    Chat Log
    """

    id = UniqIDField(gettext_lazy("ID"), primary_key=True)
    chat_id = models.CharField(
        gettext_lazy("Chat ID"), max_length=MAX_CHAR_LENGTH, db_index=True, null=True, blank=True
    )
    user = ForeignKey(gettext_lazy("User"), to="account.User", on_delete=models.PROTECT)
    model = models.CharField(
        gettext_lazy("Model"),
        max_length=MEDIUM_CHAR_LENGTH,
        null=True,
        blank=True,
        db_index=True,
    )
    prompt_tokens = models.BigIntegerField(gettext_lazy("Prompt Tokens"), default=int)
    completion_tokens = models.BigIntegerField(gettext_lazy("Completion Tokens"), default=int)
    vision_count = models.BigIntegerField(gettext_lazy("Vision Count"), default=int)
    prompt_token_unit_price = models.DecimalField(
        gettext_lazy("Prompt Token Unit Price"),
        max_digits=PRICE_DIGIT_NUMS,
        decimal_places=PRICE_DECIMAL_NUMS,
        default=float,
    )
    completion_token_unit_price = models.DecimalField(
        gettext_lazy("Completion Token Unit Price"),
        max_digits=PRICE_DIGIT_NUMS,
        decimal_places=PRICE_DECIMAL_NUMS,
        default=float,
    )
    vision_unit_price = models.DecimalField(
        gettext_lazy("Vision Unit Price"),
        max_digits=PRICE_DIGIT_NUMS,
        decimal_places=PRICE_DECIMAL_NUMS,
        default=float,
    )
    request_unit_price = models.DecimalField(
        gettext_lazy("Request Unit Price"),
        max_digits=PRICE_DIGIT_NUMS,
        decimal_places=PRICE_DECIMAL_NUMS,
        default=float,
    )
    created_at = models.BigIntegerField(gettext_lazy("Create Time"), db_index=True)
    finished_at = models.BigIntegerField(gettext_lazy("Finish Time"), db_index=True, null=True, blank=True)
    is_charged = models.BooleanField(gettext_lazy("Is Charged"), default=False, db_index=True)

    class Meta:
        verbose_name = gettext_lazy("Chat Log")
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        index_together = [
            ["finished_at", "is_charged"],
            ["user", "finished_at", "created_at"],
        ]


class AIModel(BaseModel):
    """
    AI Model
    """

    id = UniqIDField(gettext_lazy("ID"), primary_key=True)
    provider = models.CharField(
        gettext_lazy("Provider"), max_length=MEDIUM_CHAR_LENGTH, choices=AIModelProvider.choices, db_index=True
    )
    desc = models.TextField(gettext_lazy("Description"), null=True, blank=True)
    model = models.CharField(gettext_lazy("Model"), max_length=MEDIUM_CHAR_LENGTH, db_index=True)
    name = models.CharField(gettext_lazy("Model Name"), max_length=MEDIUM_CHAR_LENGTH)
    icon = models.URLField(gettext_lazy("Icon"), null=True, blank=True)
    is_enabled = models.BooleanField(gettext_lazy("Enabled"), default=True, db_index=True)
    prompt_price = models.DecimalField(
        gettext_lazy("Prompt Price"), max_digits=PRICE_DIGIT_NUMS, decimal_places=PRICE_DECIMAL_NUMS, default=0
    )
    completion_price = models.DecimalField(
        gettext_lazy("Completion Price"), max_digits=PRICE_DIGIT_NUMS, decimal_places=PRICE_DECIMAL_NUMS, default=0
    )
    vision_price = models.DecimalField(
        gettext_lazy("Vision Price"), max_digits=PRICE_DIGIT_NUMS, decimal_places=PRICE_DECIMAL_NUMS, default=0
    )
    request_price = models.DecimalField(
        gettext_lazy("Request Price"), max_digits=PRICE_DIGIT_NUMS, decimal_places=PRICE_DECIMAL_NUMS, default=0
    )
    support_system_define = models.BooleanField(gettext_lazy("Support System Define"), default=True)
    support_vision = models.BooleanField(gettext_lazy("Support Vision"), default=False)
    is_vision = models.BooleanField(gettext_lazy("Is Vision"), default=False)
    settings = models.JSONField(gettext_lazy("Settings"), blank=True, null=True)
    is_public = models.BooleanField(gettext_lazy("Is Public"), default=False)

    class Meta:
        verbose_name = gettext_lazy("AI Model")
        verbose_name_plural = verbose_name
        ordering = ["provider", "name"]
        unique_together = [["provider", "model"]]
        index_together = [["is_enabled", "is_public", "model"]]

    def __str__(self) -> str:
        return f"{self.model}"

    @classmethod
    def list_user_models(cls, user: USER_MODEL) -> QuerySet:
        return cls.objects.filter(
            Q(Q(is_enabled=True) & Q(Q(is_public=True) | Q(pk__in=user.model_permissions.all().values("models"))))
        )

    @classmethod
    def check_user_permission(cls, user: USER_MODEL, model: str) -> bool:
        if not model:
            return False
        return cls.list_user_models(user).filter(model=model).exists()


class ModelPermission(BaseModel):
    """
    Model Permission
    """

    id = UniqIDField(gettext_lazy("ID"), primary_key=True)
    user = ForeignKey(
        gettext_lazy("User"), to="account.User", on_delete=models.CASCADE, related_name="model_permissions"
    )
    models = models.ManyToManyField(
        verbose_name=gettext_lazy("Model"), to="AIModel", related_name="model_permissions", db_constraint=False
    )

    class Meta:
        verbose_name = gettext_lazy("Model Permission")
        verbose_name_plural = verbose_name
        ordering = ["user"]

    def __str__(self) -> str:
        return f"{self.user}"


class SystemPreset(BaseModel):
    """
    System Preset
    """

    id = UniqIDField(gettext_lazy("ID"), primary_key=True)
    name = models.CharField(gettext_lazy("Name"), max_length=MEDIUM_CHAR_LENGTH)
    content = models.TextField(gettext_lazy("Content"))
    is_public = models.BooleanField(gettext_lazy("Is Public"), default=False, db_index=True)
    user = ForeignKey(gettext_lazy("Owner"), to="account.User", on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(gettext_lazy("Create Time"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(gettext_lazy("Update Time"), auto_now=True)

    class Meta:
        verbose_name = gettext_lazy("System Preset")
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        index_together = ["is_public", "user", "name"]


class ChatMessageChangeLog(BaseModel):
    """
    Chat Message Change Log
    """

    id = models.BigAutoField(gettext_lazy("ID"), primary_key=True)
    user = ForeignKey(gettext_lazy("User"), to="account.User", on_delete=models.PROTECT)
    message_id = models.CharField(gettext_lazy("Message ID"), max_length=MEDIUM_CHAR_LENGTH)
    action = models.SmallIntegerField(gettext_lazy("Action"), choices=MessageSyncAction.choices)
    content = models.TextField(gettext_lazy("Content"), help_text=gettext_lazy("Encrypted Message Content"), blank=True)
    created_at = models.DateTimeField(gettext_lazy("Create Time"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = gettext_lazy("Chat Message Change Log")
        verbose_name_plural = verbose_name
        ordering = ["-id"]
        indexes = [
            Index(fields=["user", "created_at"]),
            Index(fields=["user", "message_id", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user}:{self.message_id}"
