# -*- coding=utf-8

import datetime
from io import BytesIO
from urllib.parse import quote, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.translation import gettext, gettext_lazy
from django_redis.client import DefaultClient
from ovinc_client.account.models import User
from ovinc_client.core.logger import logger
from ovinc_client.core.utils import simple_uniq_id
from pydantic import BaseModel as BaseDataModel
from qcloud_cos import CosConfig, CosS3Client
from rest_framework import status
from rest_framework.exceptions import APIException
from sts.sts import Sts

from apps.cos.constants import TEXT_AUDIT_BATCH_SIZE, AuditResult, TextAuditCallbackType
from apps.cos.exceptions import SensitiveData
from apps.cos.models import ImageAuditResponse, TextAuditResponse
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
class COSCredential(BaseDataModel):
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
        self.client = CosS3Client(self._config)

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

    def generate_cos_upload_credential(self, filename: str) -> COSCredential:
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
            "allow_actions": ["cos:PutObject"],
            "condition": {
                "numeric_less_than_equal": {"cos:content-length": settings.QCLOUD_COS_MAX_UPLOAD_SIZE},
            },
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
                use_accelerate=settings.QCLOUD_COS_USE_ACCELERATE,
                image_format=(
                    settings.QCLOUD_COS_IMAGE_STYLE if key.split(".")[-1] in settings.QCLOUD_COS_IMAGE_SUFFIX else ""
                ),
                cdn_sign=TCloudUrlParser.sign(
                    hostname=urlparse(settings.QCLOUD_COS_URL).hostname,
                    path="/" + quote(key.lstrip("/"), safe="/"),
                ),
            )
        except Exception as err:
            logger.exception("[TempKeyGenerateFailed] %s", err)
            raise TempKeyGenerateFailed() from err

    def put_object(self, file: bytes | BytesIO, file_name: str) -> str:
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
        return f"{settings.QCLOUD_COS_URL}/{key}"

    def text_audit(self, user: USER_MODEL, content: str, data_id: str = None) -> None:
        """
        Text Audit
        """

        if not settings.QCLOUD_TEXT_AUDIT_ENABLED:
            return

        for index in range(0, len(content), TEXT_AUDIT_BATCH_SIZE):
            _content = content[index : index + TEXT_AUDIT_BATCH_SIZE]
            if not _content:
                break
            response_data = self.client.ci_auditing_text_submit(
                Bucket=settings.QCLOUD_COS_BUCKET,
                BizType=settings.QCLOUD_CI_TEXT_AUDIT_BIZ_TYPE,
                Content=_content.encode("utf-8"),
                CallbackType=TextAuditCallbackType.SENSITIVE,
                UserInfo={"username": user.username},
                DataId=data_id,
            )
            response = TextAuditResponse.model_validate(response_data)
            if response.JobsDetail.Result == AuditResult.NORMAL:
                continue
            logger.warning("[TextAuditFailed] %s %s", data_id, response.model_dump_json())
            raise SensitiveData(gettext("%s Sensitive") % response.JobsDetail.Label)

    def image_audit(self, user: USER_MODEL, image_url: str, data_id: str = None) -> None:
        """
        Image Audit
        """

        if not settings.QCLOUD_IMAGE_AUDIT_ENABLED:
            return

        response_data = self.client.get_object_sensitive_content_recognition(
            Bucket=settings.QCLOUD_COS_BUCKET,
            BizType=settings.QCLOUD_CI_IMAGE_AUDIT_BIZ_TYPE,
            DetectUrl=image_url,
            LargeImageDetect=settings.QCLOUD_CI_IMAGE_AUDIT_LARGE_IMAGE,
            DataId=f"{user.username}:{data_id}",
        )
        response = ImageAuditResponse.model_validate(response_data)
        if response.Result == AuditResult.NORMAL:
            return
        logger.warning("[ImageAuditFailed] %s %s", data_id, response.model_dump_json())
        raise SensitiveData(gettext("%s Sensitive") % response.Label)
