# pylint: disable=C0103

from dataclasses import dataclass
from typing import List

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy
from ovinc_client.core.constants import (
    MAX_CHAR_LENGTH,
    MEDIUM_CHAR_LENGTH,
    SHORT_CHAR_LENGTH,
)
from ovinc_client.core.models import BaseModel, ForeignKey, UniqIDField

from apps.chat.constants import (
    PRICE_DECIMAL_NUMS,
    PRICE_DIGIT_NUMS,
    AIModelProvider,
    CurrencyUnit,
    OpenAIRole,
    VisionQuality,
    VisionSize,
    VisionStyle,
)

USER_MODEL = get_user_model()


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
    currency_unit = models.CharField(
        gettext_lazy("Currency Unit"),
        max_length=SHORT_CHAR_LENGTH,
        choices=CurrencyUnit.choices,
        default=CurrencyUnit.USD,
    )
    created_at = models.BigIntegerField(gettext_lazy("Create Time"), db_index=True)
    finished_at = models.BigIntegerField(gettext_lazy("Finish Time"), db_index=True, null=True, blank=True)
    is_charged = models.BooleanField(gettext_lazy("Is Charged"), default=False, db_index=True)

    class Meta:
        verbose_name = gettext_lazy("Chat Log")
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        index_together = [["finished_at", "is_charged"]]


@dataclass
class Message:
    """
    OpenAI Message
    """

    role: OpenAIRole
    content: str


class ModelPermission(BaseModel):
    """
    Model Permission
    """

    id = UniqIDField(gettext_lazy("ID"))
    user = ForeignKey(gettext_lazy("User"), to="account.User", on_delete=models.PROTECT)
    model = models.CharField(
        gettext_lazy("Model"),
        max_length=MEDIUM_CHAR_LENGTH,
        null=True,
        blank=True,
        db_index=True,
    )
    available_usage = models.BigIntegerField(gettext_lazy("Available Usage"), default=int, db_index=True)
    expired_at = models.DateTimeField(gettext_lazy("Expire Time"), null=True, blank=True)
    created_at = models.DateTimeField(gettext_lazy("Create Time"), auto_now_add=True)

    class Meta:
        verbose_name = gettext_lazy("Model Permission")
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        index_together = [["user", "model", "expired_at"], ["user", "available_usage", "model", "expired_at"]]
        unique_together = [["user", "model"]]

    @classmethod
    def authed_models(cls, user: USER_MODEL, model: str = None) -> QuerySet:
        # load enabled models
        queryset = AIModel.objects.filter(is_enabled=True)
        # build filter
        q = Q(user=user, available_usage__gt=0)  # pylint: disable=C0103
        if model:
            q &= Q(  # pylint: disable=C0103
                Q(model=str(model), expired_at__gt=timezone.now()) | Q(model=str(model), expired_at__isnull=True)
            )
        else:
            q &= Q(Q(expired_at__gt=timezone.now()) | Q(expired_at__isnull=True))  # pylint: disable=C0103
        # load permission
        authed_models = cls.objects.filter(q).values("model")
        # load authed models
        return queryset.filter(model__in=authed_models)


@dataclass
class HunYuanDelta:
    Role: str = ""
    Content: str = ""


@dataclass
class HunYuanChoice:
    FinishReason: str = ""
    Delta: HunYuanDelta = None


@dataclass
class HunYuanUsage:
    PromptTokens: int = 0
    CompletionTokens: int = 0
    TotalTokens: int = 0


@dataclass
class HunYuanChuck:
    Note: str = ""
    Choices: List[HunYuanChoice] = None
    Created: str = ""
    Id: str = ""
    Usage: HunYuanUsage = None

    @classmethod
    def create(cls, data: dict) -> "HunYuanChuck":
        chuck = cls(**data)
        chuck.Usage = HunYuanUsage(**data.get("Usage", {}))
        chuck.Choices = [
            HunYuanChoice(FinishReason=choice.get("FinishReason", ""), Delta=HunYuanDelta(**choice.get("Delta", {})))
            for choice in data.get("Choices", [])
        ]
        return chuck


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
    currency_unit = models.CharField(
        gettext_lazy("Currency Unit"),
        max_length=SHORT_CHAR_LENGTH,
        choices=CurrencyUnit.choices,
        default=CurrencyUnit.USD,
    )
    is_vision = models.BooleanField(gettext_lazy("Is Vision"), default=False)
    vision_size = models.CharField(
        gettext_lazy("Vision Size"),
        max_length=MEDIUM_CHAR_LENGTH,
        choices=VisionSize.choices,
        null=True,
        blank=True,
    )
    vision_quality = models.CharField(
        gettext_lazy("Vision Quality"),
        max_length=MEDIUM_CHAR_LENGTH,
        choices=VisionQuality.choices,
        null=True,
        blank=True,
    )
    vision_style = models.CharField(
        gettext_lazy("Vision Style"),
        max_length=MEDIUM_CHAR_LENGTH,
        choices=VisionStyle.choices,
        null=True,
        blank=True,
    )
    settings = models.JSONField(gettext_lazy("Settings"), blank=True, null=True)

    class Meta:
        verbose_name = gettext_lazy("AI Model")
        verbose_name_plural = verbose_name
        ordering = ["provider", "name"]
        unique_together = [["provider", "model"]]
