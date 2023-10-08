from typing import List

import tiktoken
from django.conf import settings
from django.utils.translation import gettext, gettext_lazy
from rest_framework import serializers

from apps.chat.constants import (
    MESSAGE_MIN_LENGTH,
    TEMPERATURE_DEFAULT,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    TOP_P_DEFAULT,
    TOP_P_MIN,
    OpenAIModel,
    OpenAIRole,
)

TOKEN_ENCODING = tiktoken.encoding_for_model(OpenAIModel.GPT35_TURBO)


class OpenAIMessageSerializer(serializers.Serializer):
    """
    OpenAI Message
    """

    role = serializers.ChoiceField(label=gettext_lazy("Role"), choices=OpenAIRole.choices)
    content = serializers.CharField(label=gettext_lazy("Content"))


class OpenAIRequestSerializer(serializers.Serializer):
    """
    OpenAI Request
    """

    model = serializers.ChoiceField(label=gettext_lazy("Model"), choices=OpenAIModel.choices)
    messages = serializers.ListField(
        label=gettext_lazy("Messages"), child=OpenAIMessageSerializer(), min_length=MESSAGE_MIN_LENGTH
    )
    temperature = serializers.FloatField(
        label=gettext_lazy("Temperature"),
        min_value=TEMPERATURE_MIN,
        max_value=TEMPERATURE_MAX,
        default=TEMPERATURE_DEFAULT,
        required=False,
    )
    top_p = serializers.FloatField(
        label=gettext_lazy("Top Probability"), min_value=TOP_P_MIN, default=TOP_P_DEFAULT, required=False
    )

    def validate_messages(self, messages: List[dict]) -> List[dict]:
        # make suer the messages won't be so long
        total_tokens = len(TOKEN_ENCODING.encode("".join([message["content"] for message in messages])))
        if total_tokens >= settings.OPENAI_MAX_ALLOWED_TOKENS:
            raise serializers.ValidationError(gettext("Messages too long, please clear all input"))
        return messages


class CheckModelPermissionSerializer(serializers.Serializer):
    """
    Model Permission
    """

    model = serializers.ChoiceField(label=gettext_lazy("Model"), choices=OpenAIModel.choices)


class OpenAIChatRequestSerializer(serializers.Serializer):
    """
    OpenAI Chat
    """

    key = serializers.CharField()
