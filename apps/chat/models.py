from dataclasses import dataclass

from django.db import models
from django.utils.translation import gettext_lazy

from apps.chat.constants import (
    PRICE_DECIMAL_NUMS,
    PRICE_DIGIT_NUMS,
    OpenAIModel,
    OpenAIRole,
)
from core.constants import MAX_CHAR_LENGTH, MEDIUM_CHAR_LENGTH
from core.models import BaseModel, ForeignKey, UniqIDField


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
