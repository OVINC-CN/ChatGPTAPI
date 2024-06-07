from django.conf import settings
from django.core.cache import cache
from ovinc_client.core.utils import uniq_id
from ovinc_client.core.viewsets import ListMixin, MainViewSet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.chat.models import ChatLog, ModelPermission
from apps.chat.permissions import AIModelPermission
from apps.chat.serializers import (
    CheckModelPermissionSerializer,
    OpenAIRequestSerializer,
)


# pylint: disable=R0901
class ChatViewSet(MainViewSet):
    """
    Chat
    """

    queryset = ChatLog.objects.all()

    def check_record_log(self, request: Request, *args, **kwargs) -> bool:
        if self.action == "pre_check":
            return False
        return super().check_record_log(request, *args, **kwargs)

    @action(methods=["POST"], detail=False, permission_classes=[AIModelPermission])
    def pre_check(self, request, *args, **kwargs):
        """
        pre-check before chat
        """

        # validate request
        request_serializer = OpenAIRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # cache
        cache_key = uniq_id()
        cache.set(
            key=cache_key,
            value={**request_data, "user": request.user.username},
            timeout=settings.OPENAI_PRE_CHECK_TIMEOUT,
        )

        # response
        return Response(data={"key": cache_key})


# pylint: disable=R0901
class AIModelViewSet(ListMixin, MainViewSet):
    """
    Model
    """

    def list(self, request, *args, **kwargs):
        """
        List Models
        """

        data = [{"id": model.model, "name": model.name} for model in ModelPermission.authed_models(user=request.user)]
        data.sort(key=lambda model: model["name"])
        return Response(data=data)

    @action(methods=["GET"], detail=False)
    def check(self, reqeust, *args, **kwargs):
        """
        Check Model Permission
        """

        # validate
        request_serializer = CheckModelPermissionSerializer(data=reqeust.query_params)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        return Response(
            data={
                "has_permission": ModelPermission.authed_models(user=reqeust.user, model=request_data["model"]).exists()
            }
        )
