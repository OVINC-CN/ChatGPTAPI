from django.utils.translation import gettext
from opentelemetry import trace
from opentelemetry.trace import format_trace_id

JSON_DEFAULT_INDENT = 4


def get_current_trace_id() -> str | None:
    try:
        span = trace.get_current_span()
        return format_trace_id(span.get_span_context().trace_id)
    except Exception:  # pylint: disable=W0718
        return None


def format_error(log_id: str, error: Exception) -> dict:
    message = gettext("Request Failed: %s") % str(error)
    trace_id = gettext("TraceID: %s") % get_current_trace_id()
    contact = gettext("Please contact admin for more information")
    return {
        "data": f"\n:::warning\n{message}\n{trace_id}\n{contact}\n:::\n",
        "thinking": "",
        "is_finished": True,
        "log_id": log_id,
    }


def format_response(log_id: str, data: str = "", thinking: str = "") -> dict:
    return {"data": data, "thinking": thinking, "is_finished": False, "log_id": log_id}
