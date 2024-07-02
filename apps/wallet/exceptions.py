from django.utils.translation import gettext_lazy
from rest_framework import status
from rest_framework.exceptions import APIException


class NoBalanceException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = gettext_lazy("No Balance")
