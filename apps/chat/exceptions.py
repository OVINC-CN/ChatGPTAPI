from django.utils.translation import gettext_lazy
from rest_framework import status
from rest_framework.exceptions import APIException


class NoModelPermission(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = gettext_lazy("Unauthorized Model")


class UnexpectedError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("Unknown Error")
