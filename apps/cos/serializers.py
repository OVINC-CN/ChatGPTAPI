from adrf.serializers import Serializer
from django.utils.translation import gettext, gettext_lazy
from ovinc_client.core.async_tools import SyncRunner
from ovinc_client.tcaptcha.utils import TCaptchaVerify
from rest_framework import serializers

from apps.cos.constants import FileUploadPurpose
from core.exceptions import TCaptchaVerifyFailed


class GenerateTempSecretSerializer(Serializer):
    """
    Temp Secret
    """

    filename = serializers.CharField(label=gettext_lazy("File Name"))
    purpose = serializers.ChoiceField(label=gettext_lazy("Purpose"), choices=FileUploadPurpose.choices)
    tcaptcha = serializers.JSONField(label=gettext_lazy("Tencent Captcha"), required=False, default=dict)

    def validate(self, attrs: dict) -> dict:
        data = super().validate(attrs)
        if not SyncRunner().run(
            TCaptchaVerify(user_ip=self.context.get("user_ip"), **data.pop("tcaptcha", {})).verify()
        ):
            raise TCaptchaVerifyFailed()
        return data

    def validate_filename(self, filename: str) -> str:
        if filename.find("/") != -1:
            raise serializers.ValidationError(gettext("File Name Invalid"))
        return filename
