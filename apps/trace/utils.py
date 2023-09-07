import sys
from enum import Enum
from typing import Tuple

from django.conf import settings
from opentelemetry import trace
from opentelemetry.sdk.trace import Span, Tracer


class ServiceNameHandler:
    """
    Service Name Handler
    """

    class SuffixEnum(Enum):
        """
        Service Name Suffix Enum
        """

        CELERY_BEAT = "celery-beat"
        CELERY_WORKER = "celery-worker"
        API = "api"
        NONE = ""

    def __init__(self, service_name: str):
        self._service_name = service_name

    @property
    def is_celery(self) -> bool:
        """
        Check if running celery worker
        """

        return "celery" in sys.argv

    @property
    def is_celery_beat(self) -> bool:
        """
        Check if running celery beat
        """

        return self.is_celery and "beat" in sys.argv

    @property
    def suffix(self) -> str:
        """
        Service Name Suffix
        """

        # Celery Beat
        if self.is_celery_beat:
            return self.SuffixEnum.CELERY_BEAT.value
        # Celery Worker
        if self.is_celery:
            return self.SuffixEnum.CELERY_WORKER.value
        # Default
        return self.SuffixEnum.NONE.value

    def get_service_name(self) -> str:
        """
        Get Service Name
        """

        # when has suffix, then return value with suffix
        if self.suffix:
            return "{}-{}".format(self._service_name, self.suffix)
        # return default service name
        return self._service_name


def inject_logging_trace_info(
    logging: dict, inject_formatters: Tuple[str], trace_format: str, format_keywords: Tuple[str] = ("format", "fmt")
):
    """
    Inject trace info into logging config
    """

    formatters = {name: formatter for name, formatter in logging["formatters"].items() if name in inject_formatters}
    for name, formatter in formatters.items():
        matched_keywords = set(format_keywords).intersection(set(formatter.keys()))
        for keyword in matched_keywords:
            formatter.update({keyword: formatter[keyword].strip() + f" {trace_format}\n"})


def get_tracer() -> Tracer:
    """
    Get Tracer
    """

    return trace.get_tracer(settings.APP_CODE)


def start_as_current_span(span_name: str) -> Span:
    """
    Start a Span
    """

    tracer = get_tracer()
    return tracer.start_as_current_span(span_name)
