from dataclasses import asdict

from channels.db import database_sync_to_async
from django.conf import settings
from ovinc_client.core.utils import get_ip
from ovinc_client.core.viewsets import ListMixin, MainViewSet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.cos.client import COSClient
from apps.cos.constants import FileUploadPurpose
from apps.cos.exceptions import UploadNotEnabled
from apps.cos.models import FileExtractInfo
from apps.cos.serializers import GenerateTempSecretSerializer


class COSViewSet(ListMixin, MainViewSet):
    """
    COS
    """

    async def list(self, request, *args, **kwargs):
        """
        Load Configs
        """

        return Response(
            {
                "upload_file_enabled": settings.ENABLE_FILE_UPLOAD,
                "upload_max_size": settings.QCLOUD_COS_MAX_UPLOAD_SIZE,
            }
        )

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
        data = asdict(
            await COSClient().generate_cos_upload_credential(user=request.user, filename=request_data["filename"])
        )

        # save db
        if request_data["purpose"] == FileUploadPurpose.EXTRACT:
            file_path = f"{settings.QCLOUD_COS_URL}/{data['key']}"
            await database_sync_to_async(FileExtractInfo.objects.create)(
                file_path=file_path,
                key=FileExtractInfo.build_key(file_path=file_path),
            )

        # response
        return Response(data=data)
