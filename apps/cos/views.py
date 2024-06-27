from dataclasses import asdict

from django.conf import settings
from django.core.cache import cache
from django_redis.client import DefaultClient
from ovinc_client.core.utils import get_ip
from ovinc_client.core.viewsets import ListMixin, MainViewSet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.cel.tasks import extract_file as extract_file_async
from apps.cos.client import COSClient
from apps.cos.constants import FILE_UPLOAD_CACHE_KEY, FileUploadPurpose
from apps.cos.exceptions import KeyInvalid, UploadNotEnabled
from apps.cos.serializers import ExtractFileSerializer, GenerateTempSecretSerializer

cache: DefaultClient


class COSViewSet(ListMixin, MainViewSet):
    """
    COS
    """

    async def list(self, request, *args, **kwargs):
        """
        Load Configs
        """

        return Response({"upload_file_enabled": settings.ENABLE_FILE_UPLOAD})

    @action(methods=["POST"], detail=False)
    async def temp_secret(self, request: Request, *args, **kwargs):
        """
        Generate New Temp Secret for COS
        """

        if not settings.ENABLE_FILE_UPLOAD:
            raise UploadNotEnabled()

        # validate
        serializer = GenerateTempSecretSerializer(data=request.data, context={"user_ip": get_ip(request)})
        serializer.is_valid(raise_exception=True)
        request_data = serializer.validated_data

        # generate
        data = asdict(await COSClient().generate_cos_upload_credential(filename=request_data["filename"]))

        # save cache
        if request_data["purpose"] == FileUploadPurpose.EXTRACT:
            cache.set(
                key=FILE_UPLOAD_CACHE_KEY.format(key=data["key"]),
                value=f"{settings.QCLOUD_COS_URL}{data['key']}",
                timeout=settings.FILE_EXTRACT_CACHE_TIMEOUT,
            )

        # response
        return Response(data=data)

    @action(methods=["POST"], detail=False)
    async def extract_file(self, request, *args, **kwargs):
        """
        Extract File
        """

        # validate
        serializer = ExtractFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_data = serializer.validated_data

        # load file path
        cache_key = FILE_UPLOAD_CACHE_KEY.format(key=request_data["key"])
        file_path = cache.get(key=cache_key)
        if not file_path:
            raise KeyInvalid()
        cache.delete(key=cache_key)

        # extract
        extract_file_async.apply_async(kwargs={"file_path": file_path})

        # response
        return Response()
