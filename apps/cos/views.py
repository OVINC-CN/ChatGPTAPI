from dataclasses import asdict

from ovinc_client.core.utils import get_ip
from ovinc_client.core.viewsets import MainViewSet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.cos.client import cos_client
from apps.cos.serializers import GenerateTempSecretSerializer


class COSViewSet(MainViewSet):
    """
    COS
    """

    @action(methods=["POST"], detail=False)
    async def temp_secret(self, request: Request, *args, **kwargs):
        """
        Generate New Temp Secret for COS
        """

        # validate
        serializer = GenerateTempSecretSerializer(data=request.data, context={"user_ip": get_ip(request)})
        serializer.is_valid(raise_exception=True)
        request_data = serializer.validated_data

        # generate
        data = asdict(
            await cos_client.generate_cos_upload_credential(user=request.user, filename=request_data["filename"])
        )
        return Response(data=data)
