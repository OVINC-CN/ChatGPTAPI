from django.utils.translation import gettext_lazy
from rest_framework import status
from rest_framework.exceptions import APIException


class VerifyFailed(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = gettext_lazy("Code Verify Failed")
