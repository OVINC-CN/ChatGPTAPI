from django.apps import AppConfig
from django.conf import settings
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


class TraceExtendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.trace_extend"

    def ready(self):
        if settings.ENABLE_TRACE:
            HTTPXClientInstrumentor().instrument()
