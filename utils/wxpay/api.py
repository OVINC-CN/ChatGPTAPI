import abc
from typing import Dict, List

import httpx
from django.conf import settings
from ovinc_client.core.logger import logger
from rest_framework import status

from utils.wxpay.exceptions import WxPayAPIException
from utils.wxpay.utils import WXPaySignatureTool


class WXPayAPI:
    """
    WXPay API
    """

    verify_response: bool = True

    @property
    @abc.abstractmethod
    def request_method(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def request_path(self) -> str:
        raise NotImplementedError()

    @property
    def url_keys(self) -> List[str]:
        return []

    def request(self, url_params: dict = None, data: dict = None) -> dict:
        # build params
        url = self.build_url(url_params=url_params)
        headers = self.build_headers(url=url, data=data)
        # call api
        client = httpx.Client(http2=True, headers=headers)
        try:
            response = client.request(method=self.request_method, url=url, json=data)
            logger.info(
                "[WxPayAPIResult] Method: %s; Path: %s; Status: %s",
                self.request_method,
                self.request_path,
                response.status_code,
            )
        except Exception as err:
            logger.exception(
                "[WxPayAPIFailed] Method: %s; Path: %s; Error: %s", self.request_method, self.request_path, err
            )
            raise WxPayAPIException() from err
        finally:
            client.close()
        # parse response
        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            logger.exception(
                "[WxPayAPIFailed] Method: %s; Path: %s; Status: %s; Headers: %s; Error: %s",
                self.request_method,
                self.request_path,
                response.status_code,
                response.headers,
                response.content,
            )
            raise WxPayAPIException(detail=response.json().get("message"), code=response.status_code)
        # verify
        if not self.verify_response:
            return response.json()
        WXPaySignatureTool.verify(headers=response.headers, content=response.content)
        return response.json()

    def build_url(self, url_params: dict) -> str:
        url = f"{settings.WXPAY_API_BASE_URL}{self.request_path}"
        if self.url_keys:
            url = url.format(**{key: url_params[key] for key in self.url_keys})
        return url

    def build_headers(self, url: str, data: dict = None) -> Dict[str, str]:
        signature = WXPaySignatureTool.generate(request_method=self.request_method, request_url=url, request_body=data)
        return {"Authorization": signature}


class GetCerts(WXPayAPI):
    """
    Get WXPay Certs
    """

    request_method = "GET"
    request_path = "/v3/certificates"
    verify_response = False


class NaivePrePay(WXPayAPI):
    """
    Naive PrePay API
    """

    request_method = "POST"
    request_path = "/v3/pay/transactions/native"
