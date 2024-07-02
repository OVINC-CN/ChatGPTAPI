from django.contrib import admin
from django.utils.translation import gettext_lazy

from apps.wallet.models import BillingHistory, Wallet


class UserNickNameMixin:
    @admin.display(description=gettext_lazy("Nick Name"))
    def user__nickname(self, inst: Wallet):
        return inst.user.nick_name


@admin.register(Wallet)
class WalletAdmin(UserNickNameMixin, admin.ModelAdmin):
    list_display = ["user", "user__nickname", "balance"]
    ordering = ["user"]
    search_fields = ["user__nick_name"]


@admin.register(BillingHistory)
class BillingHistoryAdmin(UserNickNameMixin, admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "user__nickname",
        "amount",
        "state",
        "is_success",
        "created_at",
        "callback_at",
    ]
    ordering = ["-created_at"]
    search_fields = ["user__nickname"]
