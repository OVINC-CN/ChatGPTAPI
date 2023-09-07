import traceback
from functools import wraps

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from core.exceptions import ServerError, exception_handler
from core.logger import logger, mysql_logger


class CSRFExemptMiddleware(MiddlewareMixin):
    """
    CSRF Token Exempt
    """

    @staticmethod
    def csrf_exempt(view_func):
        def wrapped_view(*args, **kwargs):
            return view_func(*args, **kwargs)

        wrapped_view.csrf_exempt = True
        return wraps(view_func)(wrapped_view)

    def process_request(self, request) -> None:
        setattr(request, "_dont_enforce_csrf_checks", True)
        return None


class SQLDebugMiddleware(MiddlewareMixin):
    """
    SQL Debug
    """

    def process_response(self, request, response: JsonResponse) -> JsonResponse:
        if not settings.DEBUG:
            return response

        cursor = connection.cursor()
        for sql in connection.queries:
            sql_str = sql.get("sql")
            sql_time = sql.get("time")
            if sql_str.startswith("SET"):
                continue
            try:
                cursor.execute(f"explain {sql_str}")
                explain_data = cursor.fetchall()
            except Exception:
                explain_data = []
            # [2] is table，skip table
            if not explain_data or explain_data[0][2] is None:
                continue
            msg = "[{}] {}".format(sql_time, sql_str)
            for i in explain_data:
                msg += "\n \t [{}][{}] {}".format(i[4], i[6], i)
            mysql_logger.info(msg)
        return response


class UnHandleExceptionMiddleware(MiddlewareMixin):
    """
    Handler Exceptions
    """

    def process_exception(self, request, exception: Exception) -> JsonResponse:
        msg = traceback.format_exc()
        logger.error("[unhandled exception] %s\n%s", str(exception), msg)
        return exception_handler(ServerError(), {})
