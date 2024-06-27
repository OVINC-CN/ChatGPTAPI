# -*- coding=utf-8

import datetime
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.translation import gettext_lazy
from django_redis.client import DefaultClient
from ovinc_client.account.models import User
from ovinc_client.core.logger import logger
from ovinc_client.core.utils import simple_uniq_id
from qcloud_cos import CosConfig, CosS3Client
from rest_framework import status
from rest_framework.exceptions import APIException
from sts.sts import Sts

cache: DefaultClient

USER_MODEL: User = get_user_model()


class COSUploadFailed(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("COS Upload Failed")


class TempKeyGenerateFailed(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = gettext_lazy("Temp Key Generate Failed")


# pylint: disable=R0902
@dataclass
class COSCredential:
    """
    COS Credential
    """

    cos_url: str
    cos_bucket: str
    cos_region: str
    key: str
    secret_id: str
    secret_key: str
    token: str
    start_time: int
    expired_time: int


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

    async def generate_cos_upload_credential(self, filename: str):
        key = self.build_key(file_name=filename)
        tencent_cloud_api_domain = settings.QCLOUD_API_DOMAIN_TMPL.format("sts")
        config = {
            "domain": tencent_cloud_api_domain,
            "url": f"{settings.QCLOUD_API_SCHEME}://{tencent_cloud_api_domain}",
            "duration_seconds": settings.QCLOUD_STS_EXPIRE_TIME,
            "secret_id": settings.QCLOUD_SECRET_ID,
            "secret_key": settings.QCLOUD_SECRET_KEY,
            "bucket": settings.QCLOUD_COS_BUCKET,
            "region": settings.QCLOUD_COS_REGION,
            "allow_prefix": [key],
            "allow_actions": ["name/cos:PutObject"],
        }
        try:
            sts = Sts(config)
            response = sts.get_credential()
            return COSCredential(
                cos_url=settings.QCLOUD_COS_URL,
                cos_bucket=settings.QCLOUD_COS_BUCKET,
                cos_region=settings.QCLOUD_COS_REGION,
                key=key,
                secret_id=response["credentials"]["tmpSecretId"],
                secret_key=response["credentials"]["tmpSecretKey"],
                token=response["credentials"]["sessionToken"],
                start_time=response["startTime"],
                expired_time=response["expiredTime"],
            )
        except Exception as err:
            logger.exception("[TempKeyGenerateFailed] %s", err)
            raise TempKeyGenerateFailed() from err

    async def put_object(self, file: BytesIO, file_name: str) -> str:
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
