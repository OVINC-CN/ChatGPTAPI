from django.utils.translation import gettext_lazy
from rest_framework import serializers

from apps.wallet.models import BillingHistory, Wallet


class WalletSerializer(serializers.ModelSerializer):
    """
    Wallet Serializer class
    """

    class Meta:
        model = Wallet
        fields = ["balance"]


class PreChargeSerializer(serializers.Serializer):
    """
    PreCharge Serializer class
    """

    amount = serializers.IntegerField(label=gettext_lazy("Amount"))


class NotifySerializer(serializers.Serializer):
    """
    Notify Serializer class
    """

    id = serializers.CharField(label=gettext_lazy("ID"))
    create_time = serializers.DateTimeField(label=gettext_lazy("Create Time"))
    event_type = serializers.CharField(label=gettext_lazy("Event Type"))
    resource_type = serializers.CharField(label=gettext_lazy("Resource Type"))
    resource = serializers.JSONField(label=gettext_lazy("Resource"))
    summary = serializers.CharField(label=gettext_lazy("Summary"))


class BillingHistorySerializer(serializers.ModelSerializer):
    """
    Billing History
    """

    class Meta:
        model = BillingHistory
        fields = ["id", "amount", "state", "is_success", "created_at"]
