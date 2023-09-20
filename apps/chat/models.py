import datetime
from dataclasses import dataclass
from typing import List

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy
from ovinc_client.core.constants import MAX_CHAR_LENGTH, MEDIUM_CHAR_LENGTH
from ovinc_client.core.models import BaseModel, ForeignKey, UniqIDField

from apps.chat.constants import (
    PRICE_DECIMAL_NUMS,
    PRICE_DIGIT_NUMS,
    OpenAIModel,
    OpenAIRole,
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
        choices=OpenAIModel.choices,
        max_length=MEDIUM_CHAR_LENGTH,
        null=True,
        blank=True,
        db_index=True,
    )
    messages = models.JSONField(gettext_lazy("Prompt Content"), null=True, blank=True)
    content = models.TextField(gettext_lazy("Completion Content"), null=True, blank=True)
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

    class Meta:
        verbose_name = gettext_lazy("Chat Log")
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


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
        choices=OpenAIModel.choices,
        max_length=MEDIUM_CHAR_LENGTH,
        null=True,
        blank=True,
        db_index=True,
    )
    expired_at = models.DateTimeField(gettext_lazy("Expire Time"), null=True, blank=True)
    created_at = models.DateTimeField(gettext_lazy("Create Time"), auto_now_add=True)

    class Meta:
        verbose_name = gettext_lazy("Model Permission")
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        index_together = [["user", "model", "expired_at"]]

    @classmethod
    def authed_models(cls, user: USER_MODEL, model: str = None) -> QuerySet:
        q = Q(user=user)
        if model:
            q &= Q(model=str(model))
        q &= Q(Q(expired_at__gt=datetime.datetime.now()) | Q(expired_at__isnull=True))
        return cls.objects.filter(q)


@dataclass
class HunYuanDelta:
    content: str = ""


@dataclass
class HunYuanChoice:
    finish_reason: str = ""
    delta: HunYuanDelta = None


@dataclass
class HunYuanUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class HunYuanError:
    code: int = 0
    message: str = ""


@dataclass
class HunYuanChuck:
    req_id: str = ""
    note: str = ""
    choices: List[HunYuanChoice] = None
    created: str = ""
    id: str = ""
    usage: HunYuanUsage = None
    error: HunYuanError = None

    @classmethod
    def create(cls, data: dict) -> "HunYuanChuck":
        chuck = cls(**data)
        chuck.usage = HunYuanUsage(**data.get("usage", {}))
        chuck.error = HunYuanError(**data.get("error", {}))
        chuck.choices = [
            HunYuanChoice(finish_reason=choice.get("finish_reason", ""), delta=HunYuanDelta(**choice.get("delta", {})))
            for choice in data.get("choices", [])
        ]
        return chuck
