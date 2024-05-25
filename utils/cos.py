# -*- coding=utf-8

import datetime
from io import BytesIO
from urllib.parse import quote

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy
from django_redis.client import DefaultClient
from ovinc_client.core.logger import logger
from ovinc_client.core.utils import simple_uniq_id
from qcloud_cos import CosConfig, CosS3Client
from rest_framework import status
from rest_framework.exceptions import APIException

cache: DefaultClient


class COSUploadFailed(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("COS Upload Failed")


class COSClient:
    """
    COS Client
    """

    def __init__(self) -> None:
        self._config = CosConfig(
            Region=settings.QCLOUD_COS_REGION,
            SecretId=settings.QCLOUD_COS_SECRET_ID,
            SecretKey=settings.QCLOUD_COS_SECRET_KEY,
        )
        self.client = CosS3Client(self._config)

    def build_key(self, file_name: str) -> str:
        """
        Build Key
        """

        key = (
            f"/{datetime.datetime.today().strftime('%Y%m/%d')}"
            f"/{simple_uniq_id(settings.QCLOUD_COS_RANDOM_KEY_LENGTH)}"
            f"/{quote(file_name)}"
        )
        cache_key = f"{self.__class__.__name__}:{key}"
        if cache.set(key=cache_key, value=cache_key, timeout=settings.QCLOUD_KEY_DUPLICATE_TIMEOUT, nx=True):
            return key
        return self.build_key(file_name=file_name)

    def put_object(self, file: BytesIO, file_name: str) -> str:
        """
        Upload File To COS
        """

        key = self.build_key(file_name)
        try:
            result = self.client.put_object(
                Bucket=settings.QCLOUD_COS_BUCKET,
                Body=file,
                Key=key,
            )
        except Exception as err:
            logger.exception("[UploadFileFailed] %s", err)
            raise COSUploadFailed() from err
        logger.info("[UploadFileSuccess] %s %s", key, result)
        return f"{settings.QCLOUD_COS_URL}{key}"


cos_client = COSClient()
