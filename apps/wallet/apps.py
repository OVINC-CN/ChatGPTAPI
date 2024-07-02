from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class WalletConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.wallet"
    verbose_name = gettext_lazy("Wallet")
