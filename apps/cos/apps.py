from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class CosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cos"
    verbose_name = gettext_lazy("COS")
