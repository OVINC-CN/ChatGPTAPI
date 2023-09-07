from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.account"
    verbose_name = gettext_lazy("User Account")
