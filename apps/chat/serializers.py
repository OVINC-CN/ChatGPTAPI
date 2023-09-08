from django.utils.translation import gettext_lazy
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


class CheckModelPermissionSerializer(serializers.Serializer):
    """
    Model Permission
    """

    model = serializers.ChoiceField(label=gettext_lazy("Model"), choices=OpenAIModel.choices)
