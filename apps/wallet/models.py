from django.db import models, transaction
from django.db.models import F
from django.utils.translation import gettext_lazy
from ovinc_client.core.models import BaseModel, ForeignKey, UniqIDField

from utils.wxpay.constants import TradeStatus


class Wallet(BaseModel):
    """
    Wallet
    """

    id = UniqIDField(gettext_lazy("ID"), primary_key=True)
    user = models.OneToOneField(
        verbose_name=gettext_lazy("User"), to="account.User", on_delete=models.PROTECT, db_constraint=False
    )
    balance = models.DecimalField(gettext_lazy("Balance"), decimal_places=10, max_digits=20, default=0)

    class Meta:
        verbose_name = gettext_lazy("Wallet")
        verbose_name_plural = verbose_name
        ordering = ["user"]


class BillingHistory(BaseModel):
    """
    Billing History
    """

    id = UniqIDField(gettext_lazy("ID"), primary_key=True)
    user = ForeignKey(gettext_lazy("User"), to="account.User", on_delete=models.PROTECT)
    amount = models.IntegerField(gettext_lazy("Amount"))
    state = models.CharField(gettext_lazy("Message"), max_length=32, null=True, blank=True, choices=TradeStatus.choices)
    is_success = models.BooleanField(gettext_lazy("Is Success"), default=False)
    created_at = models.DateTimeField(gettext_lazy("Created Time"), auto_now_add=True, db_index=True)
    callback_at = models.DateTimeField(gettext_lazy("Callback Time"), blank=True, null=True)
    callback_data = models.JSONField(gettext_lazy("Callback Data"), null=True, blank=True)

    class Meta:
        verbose_name = gettext_lazy("Billing History")
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        index_together = [
            ["user", "created_at"],
        ]

    @transaction.atomic
    def save_to_wallet(self, *args, **kwargs):
        if self.state == TradeStatus.SUCCESS:
            Wallet.objects.get_or_create(user=self.user)
            Wallet.objects.filter(user=self.user).update(balance=F("balance") + self.amount)
        self.save(*args, **kwargs)
