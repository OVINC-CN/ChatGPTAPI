from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class HomeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.home"
    verbose_name = gettext_lazy("Home Module")
