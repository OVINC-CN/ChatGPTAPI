# pylint: disable=C0103

from typing import List

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy
from ovinc_client.core.constants import MAX_CHAR_LENGTH, MEDIUM_CHAR_LENGTH
from ovinc_client.core.models import BaseModel, ForeignKey, UniqIDField
from pydantic import BaseModel as BaseDataModel

from apps.chat.constants import (
    PRICE_DECIMAL_NUMS,
    PRICE_DIGIT_NUMS,
    AIModelProvider,
    MessageContentType,
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
    temperature: float
    top_p: float


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
    prompt_tokens = models.IntegerField(gettext_lazy("Prompt Tokens"), default=int)
    completion_tokens = models.IntegerField(gettext_lazy("Completion Tokens"), default=int)
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
    is_enabled = models.BooleanField(gettext_lazy("Enabled"), default=True, db_index=True)
    prompt_price = models.DecimalField(
        gettext_lazy("Prompt Price"), max_digits=PRICE_DIGIT_NUMS, decimal_places=PRICE_DECIMAL_NUMS
    )
    completion_price = models.DecimalField(
        gettext_lazy("Completion Price"), max_digits=PRICE_DIGIT_NUMS, decimal_places=PRICE_DECIMAL_NUMS
    )
    vision_price = models.DecimalField(
        gettext_lazy("Vision Price"), max_digits=PRICE_DIGIT_NUMS, decimal_places=PRICE_DECIMAL_NUMS, default=0
    )
    support_system_define = models.BooleanField(gettext_lazy("Support System Define"), default=True)
    support_vision = models.BooleanField(gettext_lazy("Support Vision"), default=False)
    is_vision = models.BooleanField(gettext_lazy("Is Vision"), default=False)
    settings = models.JSONField(gettext_lazy("Settings"), blank=True, null=True)

    class Meta:
        verbose_name = gettext_lazy("AI Model")
        verbose_name_plural = verbose_name
        ordering = ["provider", "name"]
        unique_together = [["provider", "model"]]


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
