from django.utils.translation import gettext_lazy
from rest_framework import status
from rest_framework.exceptions import APIException


class WxPayAPIException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("WxPay API Error")


class WxPayCertNotFound(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("WxPay Cert Not Found")


class WxPayInsecureResponse(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("WxPay Insecure Response")
