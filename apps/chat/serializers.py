import datetime

import pytz
from adrf.serializers import ModelSerializer, Serializer
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy
from rest_framework import serializers

from apps.chat.constants import MESSAGE_MIN_LENGTH, MessageSyncAction, OpenAIRole
from apps.chat.models import ChatLog, ChatMessageChangeLog, SystemPreset


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
            "vision_count",
            "prompt_token_unit_price",
            "completion_token_unit_price",
            "vision_unit_price",
            "request_unit_price",
            "created_at",
        ]

    def get_model_name(self, obj: ChatLog) -> str:
        return self.context.get("model_map", {}).get(obj.model, obj.model)

    def get_created_at(self, obj: ChatLog) -> str:
        _datetime = datetime.datetime.fromtimestamp(obj.created_at / 1000, tz=pytz.timezone(settings.TIME_ZONE))
        return _datetime.strftime("%y/%m/%d %H:%M:%S")


class MessageChangeLogSerializer(ModelSerializer):
    """
    Message Change Log
    """

    class Meta:
        model = ChatMessageChangeLog
        fields = ["message_id", "action", "content"]


class ListMessageChangeLogSerializer(Serializer):
    """
    List Message Change Log
    """

    start_time = serializers.IntegerField(label=gettext_lazy("Start Time"), required=False, allow_null=True)

    def validate_start_time(self, start_time: int) -> datetime.datetime:
        try:
            return datetime.datetime.fromtimestamp(start_time, tz=timezone.get_current_timezone())
        except ValueError as err:
            raise serializers.ValidationError(gettext_lazy("Invalid Start Time")) from err


class CreateMessageChangeLogSerializer(Serializer):
    """
    Create Message Change Log
    """

    message_id = serializers.CharField(label=gettext_lazy("Message ID"))
    action = serializers.ChoiceField(label=gettext_lazy("Action"), choices=MessageSyncAction.choices)
    content = serializers.CharField(label=gettext_lazy("Content"), allow_blank=True)
