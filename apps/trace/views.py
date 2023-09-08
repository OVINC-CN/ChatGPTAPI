from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response

from core.auth import SessionAuthenticate
from core.viewsets import MainViewSet


class RUMViewSet(MainViewSet):
    authentication_classes = [SessionAuthenticate]

    @action(methods=["GET"], detail=False)
    def config(self, request, *args, **kwargs):
        return Response(
            {
                "id": settings.RUM_ID,
                "reportApiSpeed": True,
                "reportAssetSpeed": True,
                "spa": True,
                "hostUrl": settings.RUM_HOST,
            }
        )
