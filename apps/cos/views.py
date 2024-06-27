from dataclasses import asdict

from channels.db import database_sync_to_async
from django.conf import settings
from django.shortcuts import get_object_or_404
from ovinc_client.core.utils import get_ip
from ovinc_client.core.viewsets import ListMixin, MainViewSet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.cel.tasks import extract_file as extract_file_async
from apps.cos.client import COSClient
from apps.cos.constants import FileUploadPurpose
from apps.cos.exceptions import UploadNotEnabled
from apps.cos.models import FileExtractInfo
from apps.cos.serializers import (
    ExtractFileSerializer,
    ExtractFileStatusSerializer,
    GenerateTempSecretSerializer,
)


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

        # save db
        if request_data["purpose"] == FileUploadPurpose.EXTRACT:
            file_path = f"{settings.QCLOUD_COS_URL}{data['key']}"
            await database_sync_to_async(FileExtractInfo.objects.create)(
                file_path=file_path,
                key=FileExtractInfo.build_key(file_path=file_path),
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

        # load file
        file_extract_info = await database_sync_to_async(get_object_or_404)(
            FileExtractInfo, key=FileExtractInfo.build_key(file_path=request_data["file_path"])
        )

        # extract
        extract_file_async.apply_async(kwargs={"key": file_extract_info.key})

        # response
        return Response()

    @action(methods=["GET"], detail=False)
    async def extract_file_status(self, request, *args, **kwargs):
        """
        Extract File Status
        """

        # validate
        serializer = ExtractFileSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        request_data = serializer.validated_data

        # load file
        file_extract_info = await database_sync_to_async(get_object_or_404)(
            FileExtractInfo, key=FileExtractInfo.build_key(file_path=request_data["file_path"])
        )

        # response
        response_serializer = ExtractFileStatusSerializer(instance=file_extract_info)
        return Response(await response_serializer.adata)
