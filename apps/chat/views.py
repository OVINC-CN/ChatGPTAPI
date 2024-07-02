from typing import List

from channels.db import database_sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ovinc_client.core.auth import SessionAuthenticate
from ovinc_client.core.paginations import NumPagination
from ovinc_client.core.utils import uniq_id
from ovinc_client.core.viewsets import ListMixin, MainViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.chat.models import AIModel, ChatLog, SystemPreset
from apps.chat.permissions import AIModelPermission
from apps.chat.serializers import (
    ChatLogSerializer,
    OpenAIRequestSerializer,
    SystemPresetSerializer,
)
from apps.chat.tools import TOOLS


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
        await database_sync_to_async(get_object_or_404)(AIModel, model=request_data["model"], is_enabled=True)

        # cache
        cache_key = uniq_id()
        cache.set(
            key=cache_key,
            value={**request_data, "user": request.user.username},
            timeout=settings.OPENAI_PRE_CHECK_TIMEOUT,
        )

        # response
        return Response(data={"key": cache_key})

    @action(methods=["GET"], detail=False, authentication_classes=[SessionAuthenticate])
    async def logs(self, request, *args, **kwargs):
        """
        chat logs
        """

        if not request.user.is_authenticated:
            return Response(data={"total": 0, "current": 1, "results": []})

        queryset = ChatLog.objects.filter(user=request.user)

        page = NumPagination()
        paged_queryset = await database_sync_to_async(page.paginate_queryset)(
            queryset=queryset, request=request, view=self
        )

        model_map = await self.load_model_map()
        serializer = ChatLogSerializer(instance=paged_queryset, many=True, context={"model_map": model_map})

        return page.get_paginated_response(data=await serializer.adata)

    @database_sync_to_async
    def load_model_map(self) -> dict:
        models = AIModel.objects.all()
        return {model.model: model.name for model in models}


# pylint: disable=R0901
class AIModelViewSet(ListMixin, MainViewSet):
    """
    Model
    """

    async def list(self, request, *args, **kwargs):
        """
        List Models
        """

        data = [
            {"id": model.model, "name": model.name, "desc": model.desc or ""}
            for model in await self.list_models(request)
        ]
        data.sort(key=lambda model: model["name"])
        return Response(data=data)

    @database_sync_to_async
    def list_models(self, request) -> List[AIModel]:
        return list(AIModel.objects.filter(is_enabled=True))


class SystemPresetViewSet(ListMixin, MainViewSet):
    """
    System Preset
    """

    queryset = SystemPreset.objects.all()

    async def list(self, request, *args, **kwargs):
        """
        List System Presets
        """

        queryset = SystemPreset.get_queryset().filter(Q(Q(is_public=True) | Q(user=request.user))).order_by("name")
        return Response(await SystemPresetSerializer(instance=queryset, many=True).adata)


class ToolsViewSet(ListMixin, MainViewSet):
    """
    Tools
    """

    async def list(self, request, *args, **kwargs):
        """
        List Tools
        """

        if not settings.CHATGPT_TOOLS_ENABLED:
            return Response(data=[])

        return Response(
            data=[
                {"id": tool.name, "name": str(tool.name_alias), "desc": str(tool.desc_alias)} for tool in TOOLS.values()
            ]
        )
