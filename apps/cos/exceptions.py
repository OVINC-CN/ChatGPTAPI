from django.utils.translation import gettext_lazy
from rest_framework import status
from rest_framework.exceptions import APIException


class UploadNotEnabled(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("Upload File Not Enabled")


class KeyInvalid(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = gettext_lazy("File Key Invalid")


class ExtractFailed(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("Extract Failed")


class SensitiveData(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = gettext_lazy("Sensitive Data")
