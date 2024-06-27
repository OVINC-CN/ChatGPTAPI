import hashlib
from typing import List

from adrf.serializers import Serializer
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext, gettext_lazy
from rest_framework import serializers

from apps.chat.constants import (
    MESSAGE_MIN_LENGTH,
    TEMPERATURE_DEFAULT,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    TOKEN_ENCODING,
    TOP_P_DEFAULT,
    TOP_P_MIN,
    OpenAIRole,
)
from apps.chat.exceptions import FileNotReady
from apps.cos.constants import FILE_CONTENT_CACHE_KEY


class OpenAIMessageSerializer(Serializer):
    """
    OpenAI Message
    """

    role = serializers.ChoiceField(label=gettext_lazy("Role"), choices=OpenAIRole.choices)
    file = serializers.CharField(label=gettext_lazy("File"), required=False, allow_null=True, allow_blank=True)
    content = serializers.CharField(label=gettext_lazy("Content"))


class OpenAIRequestSerializer(Serializer):
    """
    OpenAI Request
    """

    model = serializers.CharField(label=gettext_lazy("Model"))
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
        """
        make sure the messages won't be so long
        """
        # load file
        for message in messages:
            file = message.get("file")
            if not file:
                continue
            key = FILE_CONTENT_CACHE_KEY.format(file_path_sha256=hashlib.sha256(file.encode()).hexdigest())
            file_content = cache.get(key=key)
            if not file_content:
                raise FileNotReady()
            file_content = gettext('The content of file is: %s') % file_content
            message["content"] = f"{message['content']}\n{file_content}"
        # check tokens
        total_tokens = len(TOKEN_ENCODING.encode("".join([message["content"] for message in messages])))
        if total_tokens >= settings.OPENAI_MAX_ALLOWED_TOKENS:
            raise serializers.ValidationError(gettext("Messages too long, please clear all input"))
        return messages


class CheckModelPermissionSerializer(Serializer):
    """
    Model Permission
    """

    model = serializers.CharField(label=gettext_lazy("Model"))


class OpenAIChatRequestSerializer(Serializer):
    """
    OpenAI Chat
    """

    key = serializers.CharField()
