# -*- coding=utf-8

import datetime
import json
import time
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import quote

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.translation import gettext_lazy
from django_redis.client import DefaultClient
from httpx._types import FileTypes
from ovinc_client.account.models import User
from ovinc_client.core.logger import logger
from ovinc_client.core.utils import simple_uniq_id
from qcloud_cos import CosConfig, CosS3Client
from rest_framework import status
from rest_framework.exceptions import APIException
from tencentcloud.common.credential import Credential
from tencentcloud.common.exception import TencentCloudSDKException
from tencentcloud.sts.v20180813 import models as sts_models
from tencentcloud.sts.v20180813.sts_client import StsClient

from apps.cos.utils import TCloudUrlParser

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
    use_accelerate: bool
    cdn_sign: str
    cdn_sign_param: str = settings.QCLOUD_CDN_SIGN_KEY_URL_PARAM
    image_format: str = ""


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
        self.cos_client = CosS3Client(self._config)
        self._cred = Credential(
            secret_id=settings.QCLOUD_COS_SECRET_ID,
            secret_key=settings.QCLOUD_COS_SECRET_KEY,
        )
        self.sts_client = StsClient(self._cred, region=settings.QCLOUD_COS_REGION)

    def build_key(self, file_name: str) -> str:
        """
        Build Key
        """

        key = (
            f"{datetime.datetime.today().strftime('%Y%m/%d')}"
            f"/{simple_uniq_id(settings.QCLOUD_COS_RANDOM_KEY_LENGTH)}"
            f"/{file_name}"
        )
        cache_key = f"{self.__class__.__name__}:{key}"
        if cache.set(key=cache_key, value=cache_key, timeout=settings.QCLOUD_KEY_DUPLICATE_TIMEOUT, nx=True):
            return key
        return self.build_key(file_name=file_name)

    async def generate_cos_upload_credential(self, user: USER_MODEL, filename: str) -> COSCredential:
        key = self.build_key(file_name=filename)
        resource = (
            f"qcs::cos:{settings.QCLOUD_COS_REGION}:"
            f"uid/{settings.QCLOUD_COS_BUCKET.rsplit('-', 1)[-1]}:"
            f"{settings.QCLOUD_COS_BUCKET}/{key}"
        )
        req = sts_models.GetFederationTokenRequest()
        req.from_json_string(
            json.dumps(
                {
                    "Name": user.username,
                    "Policy": quote(
                        json.dumps(
                            {
                                "statement": [
                                    {
                                        "action": [
                                            "cos:PutObject",
                                        ],
                                        "condition": {
                                            "string_like": {
                                                "cos:content-type": "image/*",
                                            },
                                        },
                                        "effect": "allow",
                                        "resource": [resource],
                                    },
                                    {
                                        "action": [
                                            "cos:InitiateMultipartUpload",
                                        ],
                                        "effect": "allow",
                                        "resource": [resource],
                                        "condition": {
                                            "string_like": {
                                                "cos:content-type": "image/*",
                                            },
                                        },
                                    },
                                    {
                                        "action": [
                                            "cos:UploadPart",
                                            "cos:CompleteMultipartUpload",
                                            "cos:ListMultipartUploads",
                                            "cos:ListParts",
                                        ],
                                        "effect": "allow",
                                        "resource": [resource],
                                    },
                                ],
                                "version": "2.0",
                            }
                        )
                    ),
                    "DurationSeconds": settings.QCLOUD_STS_EXPIRE_TIME,
                }
            )
        )
        try:
            response: sts_models.GetFederationTokenResponse = self.sts_client.GetFederationToken(req)
            return COSCredential(
                cos_url=settings.QCLOUD_COS_URL,
                cos_bucket=settings.QCLOUD_COS_BUCKET,
                cos_region=settings.QCLOUD_COS_REGION,
                key=key,
                secret_id=response.Credentials.TmpSecretId,
                secret_key=response.Credentials.TmpSecretKey,
                token=response.Credentials.Token,
                start_time=int(time.time()),
                expired_time=response.ExpiredTime,
                use_accelerate=settings.QCLOUD_COS_USE_ACCELERATE,
                image_format=settings.QCLOUD_COS_IMAGE_STYLE
                if key.split(".")[-1] in settings.QCLOUD_COS_IMAGE_SUFFIX
                else "",
                cdn_sign=TCloudUrlParser.sign("/" + quote(key)),
            )
        except TencentCloudSDKException as err:
            logger.exception("[TempKeyGenerateFailed] %s", err)
            raise TempKeyGenerateFailed() from err

    async def put_object(self, file: BytesIO, file_name: str) -> str:
        """
        Upload File To COS
        """

        key = self.build_key(file_name)
        try:
            result = self.cos_client.put_object(
                Bucket=settings.QCLOUD_COS_BUCKET,
                Body=file,
                Key=key,
            )
        except Exception as err:
            logger.exception("[UploadFileFailed] %s", err)
            raise COSUploadFailed() from err
        logger.info("[UploadFileSuccess] %s %s", key, result)
        return f"{settings.QCLOUD_COS_URL}/{key}"


class MoonshotClient:
    """
    Moonshot Client
    """

    def __init__(self) -> None:
        self.client = httpx.Client(
            http2=True,
            headers={"Authorization": f"Bearer {settings.KIMI_API_KEY}"},
            base_url=settings.KIMI_API_BASE_URL,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def upload_file(self, file: FileTypes) -> dict:
        """
        Upload File To Moonshot

        .e.g
         {
            "id": "1",
            "object": "file",
            "bytes": 82246,
            "created_at": 1719484145,
            "filename": "1.png",
            "purpose": "file-extract",
            "status": "ok",
            "status_details": ""
        }
        """

        return self.client.post(url="/files", data={"purpose": "file-extract"}, files={"file": file}).json()

    def extract_file(self, file_id: str) -> dict:
        """
        Extract file into string

        .e.g
        {
            "content": "Some Content",
            "file_type": "image/png",
            "filename": "1.png",
            "title": "",
            "type": "file"
        }
        """

        return self.client.get(url=f"/files/{file_id}/content").json()

    def delete_file(self, file_id: str) -> None:
        """
        Delete file from Moonshot
        """

        return self.client.delete(url=f"/files/{file_id}").json()
