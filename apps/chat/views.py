from typing import List

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from ovinc_client.core.utils import uniq_id
from ovinc_client.core.viewsets import ListMixin, MainViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.chat.models import AIModel, ChatLog, ModelPermission
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

    @action(methods=["POST"], detail=False, permission_classes=[AIModelPermission])
    async def pre_check(self, request, *args, **kwargs):
        """
        pre-check before chat
        """

        # validate request
        request_serializer = OpenAIRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # check model
        await sync_to_async(get_object_or_404)(AIModel, model=request_data["model"], is_enabled=True)

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

    async def list(self, request, *args, **kwargs):
        """
        List Models
        """

        data = [{"id": model.model, "name": model.name} for model in await self.list_models(request)]
        data.sort(key=lambda model: model["name"])
        return Response(data=data)

    @database_sync_to_async
    def list_models(self, request) -> List[AIModel]:
        return list(ModelPermission.authed_models(user=request.user))

    @action(methods=["GET"], detail=False)
    async def check(self, request, *args, **kwargs):
        """
        Check Model Permission
        """

        # validate
        request_serializer = CheckModelPermissionSerializer(data=request.query_params)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # check model
        await sync_to_async(get_object_or_404)(AIModel, model=request_data["model"], is_enabled=True)

        return Response(data={"has_permission": await self.check_model_permission(request, request_data)})

    @database_sync_to_async
    def check_model_permission(self, request, request_data):
        return ModelPermission.authed_models(user=request.user, model=request_data["model"]).exists()
