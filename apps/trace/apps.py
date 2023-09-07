from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy

from apps.trace.setup import TraceHandler


class ApmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.trace"
    verbose_name = gettext_lazy("App Performance")

    def ready(self):
        if settings.ENABLE_TRACE:
            TraceHandler.setup()
