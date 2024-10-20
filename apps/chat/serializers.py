import datetime
from typing import List

import pytz
from adrf.serializers import ModelSerializer, Serializer
from channels.db import database_sync_to_async
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext, gettext_lazy
from ovinc_client.core.async_tools import SyncRunner
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
from apps.chat.exceptions import FileExtractFailed, FileNotReady
from apps.chat.models import ChatLog, SystemPreset
from apps.cos.models import FileExtractInfo


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
            file_content = gettext("The content of file is: %s") % SyncRunner().run(
                self.load_file_content(file_path=file)
            )
            message["content"] = f"{message['content']}\n{file_content}"
        # check tokens
        total_tokens = len(TOKEN_ENCODING.encode("".join([message["content"] for message in messages])))
        if total_tokens >= settings.OPENAI_MAX_ALLOWED_TOKENS:
            raise serializers.ValidationError(gettext("Messages too long, please clear all input"))
        return messages

    @database_sync_to_async
    def load_file_content(self, file_path: str) -> str:
        file_extract_info = get_object_or_404(FileExtractInfo, key=FileExtractInfo.build_key(file_path=file_path))
        if not file_extract_info.is_finished:
            raise FileNotReady()
        if not file_extract_info.is_success:
            raise FileExtractFailed()
        return file_extract_info.extract_info["content"]


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


class SystemPresetSerializer(ModelSerializer):
    """
    System Preset
    """

    class Meta:
        model = SystemPreset
        exclude = ["user", "created_at", "updated_at"]


class SerializerMethodField(serializers.SerializerMethodField):
    async def ato_representation(self, value):
        return super().to_representation(value)


class ChatLogSerializer(ModelSerializer):
    """
    Chat Log
    """

    model_name = SerializerMethodField()
    created_at = SerializerMethodField()

    class Meta:
        model = ChatLog
        fields = [
            "id",
            "model_name",
            "prompt_tokens",
            "completion_tokens",
            "prompt_token_unit_price",
            "completion_token_unit_price",
            "created_at",
        ]

    def get_model_name(self, obj: ChatLog) -> str:
        return self.context.get("model_map", {}).get(obj.model, obj.model)

    def get_created_at(self, obj: ChatLog) -> str:
        _datetime = datetime.datetime.fromtimestamp(obj.created_at / 1000, tz=pytz.timezone(settings.TIME_ZONE))
        return _datetime.strftime("%y/%m/%d %H:%M:%S")
