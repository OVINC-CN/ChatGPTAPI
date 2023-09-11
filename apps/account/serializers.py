from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy
from rest_framework import serializers

from apps.account.models import User

USER_MODEL: User = get_user_model()


class UserSignInSerializer(serializers.Serializer):
    """
    Sign In
    """

    code = serializers.CharField(label=gettext_lazy("Code"))


class UserInfoSerializer(serializers.ModelSerializer):
    """
    User Info
    """

    class Meta:
        model = USER_MODEL
        fields = ["username", "nick_name", "user_type", "last_login"]
