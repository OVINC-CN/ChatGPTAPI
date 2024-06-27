from django.utils.translation import gettext_lazy
from rest_framework import status
from rest_framework.exceptions import APIException


class NoModelPermission(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = gettext_lazy("Unauthorized Model")


class UnexpectedError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("Unknown Error")


class VerifyFailed(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = gettext_lazy("Pre Check Verify Failed")


class UnexpectedProvider(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = gettext_lazy("Unexpected Provider")


class LoadImageFailed(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("Load Image Failed")


class GenerateFailed(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("Generate Failed, Please Try Again")


class FileNotReady(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = gettext_lazy("File Not Ready, Please Wait Seconds and Try Again")
