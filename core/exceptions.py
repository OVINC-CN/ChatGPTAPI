from typing import Union

from django.http import Http404, JsonResponse
from django.utils.translation import gettext, gettext_lazy
from rest_framework import exceptions, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.serializers import Serializer

from apps.trace.constants import SPAN_ERROR_TYPE, SpanAttributes
from apps.trace.utils import start_as_current_span


def get_field_name(serializer: Serializer, field: str) -> str:
    """
    Get Field Name from Serialzier
    """

    serializer_field = serializer.fields.fields.get(field)
    if not serializer_field:
        return field
    return serializer_field.label


def exception_handler(exc, context) -> Union[JsonResponse, None]:
    """
    Handler Exception from Raise
    """

    if isinstance(exc, Http404):
        exc = Error404()

    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, "auth_header", None):
            headers["WWW-Authenticate"] = exc.auth_header
        if getattr(exc, "wait", None):
            headers["Retry-After"] = "%d" % exc.wait

        if isinstance(exc, ValidationError):
            if isinstance(exc.detail, dict):
                data = [exc.detail]
            else:
                data = exc.detail
            msg = ""
            for err in data:
                for field, val in err.items():
                    try:
                        msg_val = "".join(val)
                    except TypeError:
                        msg_val = str(val)
                    msg += "[{}]{}".format(get_field_name(err.serializer, field), msg_val)
        elif isinstance(exc.detail, (list, dict)):
            data = exc.detail
            msg = gettext("Request Failed")
        else:
            data = None
            msg = exc.detail

        from rest_framework.views import set_rollback

        set_rollback()

        request = context.get("request") if isinstance(context, dict) else None

        with start_as_current_span(exc.__class__.__name__) as span:
            span.set_attribute(SpanAttributes.ERROR_KIND, SPAN_ERROR_TYPE)
            span.set_attribute(SpanAttributes.ERROR_OBJECT, exc.__class__.__name__)
            span.set_attribute(SpanAttributes.ERROR_MESSAGE, msg)

        return JsonResponse(
            {
                "data": data,
                "message": msg,
                "trace": getattr(request, "otel_trace_id", None),
            },
            status=exc.status_code,
            headers=headers,
            json_dumps_params={"ensure_ascii": False},
        )

    return None


def django_exception_handler(handler, request) -> JsonResponse:
    return JsonResponse(
        {
            "data": None,
            "message": handler.default_detail,
            "trace": getattr(request, "otel_trace_id", ""),
        },
        status=handler.status_code,
        json_dumps_params={"ensure_ascii": False},
    )


def bad_request(request, exception) -> JsonResponse:
    return django_exception_handler(OperationError, request)


def permission_denied(request, exception) -> JsonResponse:
    return django_exception_handler(PermissionDenied, request)


def page_not_found(request, exception) -> JsonResponse:
    return django_exception_handler(Error404, request)


def server_error(request) -> JsonResponse:
    return django_exception_handler(ServerError, request)


def service_closed(request, exception) -> JsonResponse:
    return django_exception_handler(ServiceClosed, request)


class ServerError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("Server Error")


class LoginRequired(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = gettext_lazy("Login Required")


class LoginFailed(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = gettext_lazy("Login Failed")


class PermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = gettext_lazy("Permission Denied")


class OperationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = gettext_lazy("Operate Error")


class Error404(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = gettext_lazy("Resource Not Found")


class ServiceClosed(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("Service Closed")
