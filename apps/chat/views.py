import datetime

from django.conf import settings
from django.core.cache import cache
from django.db.models import OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ovinc_client.core.auth import SessionAuthenticate
from ovinc_client.core.paginations import NumPagination
from ovinc_client.core.utils import uniq_id
from ovinc_client.core.viewsets import CreateMixin, ListMixin, MainViewSet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.chat.constants import MESSAGE_CACHE_KEY, MessageContentType
from apps.chat.models import (
    AIModel,
    ChatLog,
    ChatMessageChangeLog,
    ChatRequest,
    MessageContent,
    MessageContentImageUrl,
    SystemPreset,
)
from apps.chat.permissions import AIModelPermission
from apps.chat.serializers import (
    ChatLogSerializer,
    CreateMessageChangeLogSerializer,
    ListMessageChangeLogSerializer,
    MessageChangeLogSerializer,
    OpenAIRequestSerializer,
    SystemPresetSerializer,
)
from apps.cos.utils import TCloudUrlParser


# pylint: disable=R0901
class ChatViewSet(MainViewSet):
    """
    Chat
    """

    queryset = ChatLog.objects.all()

    @action(methods=["POST"], detail=False, permission_classes=[AIModelPermission])
    def pre_check(self, request, *args, **kwargs):
        """
        pre-check before chat
        """

        # validate request
        request_serializer = OpenAIRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        request_data = ChatRequest(user=request.user.username, **request_serializer.validated_data)

        # check model
        model: AIModel = get_object_or_404(AIModel, model=request_data.model, is_enabled=True)

        # format message
        for message in request_data.messages:
            if message.file and model.support_vision:
                message.content = [
                    MessageContent(type=MessageContentType.TEXT, text=message.content),
                    MessageContent(
                        type=MessageContentType.IMAGE_URL,
                        image_url=MessageContentImageUrl(url=TCloudUrlParser(message.file).url),
                    ),
                ]

        # cache
        cache_key = MESSAGE_CACHE_KEY.format(uniq_id())
        cache.set(
            key=cache_key,
            value=request_data.model_dump(exclude_none=True),
            timeout=settings.OPENAI_PRE_CHECK_TIMEOUT,
        )

        # response
        return Response(data={"key": cache_key})

    @action(methods=["GET"], detail=False, authentication_classes=[SessionAuthenticate])
    def logs(self, request, *args, **kwargs):
        """
        chat logs
        """

        if not request.user.is_authenticated:
            return Response(data={"total": 0, "current": 1, "results": []})

        queryset = (
            ChatLog.objects.filter(user=request.user)
            .filter(
                finished_at__isnull=False,
                finished_at__gt=(timezone.now() - datetime.timedelta(days=settings.CHATLOG_QUERY_DAYS)).timestamp()
                * 1000,
            )
            .order_by("-created_at")
        )

        page = NumPagination()
        paged_queryset = page.paginate_queryset(queryset=queryset, request=request, view=self)

        model_map = {model.model: model.name for model in AIModel.objects.all()}
        serializer = ChatLogSerializer(instance=paged_queryset, many=True, context={"model_map": model_map})

        return page.get_paginated_response(data=serializer.data)


# pylint: disable=R0901
class AIModelViewSet(ListMixin, MainViewSet):
    """
    Model
    """

    def list(self, request, *args, **kwargs):
        """
        List Models
        """

        data = [
            {
                "id": model.model,
                "name": model.name,
                "desc": model.desc or "",
                "prompt_price": float(model.prompt_price),
                "completion_price": float(model.completion_price),
                "vision_price": float(model.vision_price),
                "request_price": float(model.request_price),
                "icon": model.icon,
                "config": {
                    "support_system_define": model.support_system_define,
                    "support_vision": model.support_vision,
                },
            }
            for model in AIModel.list_user_models(request.user)
        ]
        data.sort(key=lambda model: model["name"])
        return Response(data=data)


class SystemPresetViewSet(ListMixin, MainViewSet):
    """
    System Preset
    """

    queryset = SystemPreset.objects.all()

    def list(self, request, *args, **kwargs):
        """
        List System Presets
        """

        queryset = SystemPreset.get_queryset().filter(Q(Q(is_public=True) | Q(user=request.user))).order_by("name")
        return Response(SystemPresetSerializer(instance=queryset, many=True).data)


class ChatMessageChangeLogView(ListMixin, CreateMixin, MainViewSet):
    """
    Chat Message Change Log
    """

    queryset = ChatMessageChangeLog.objects.all()

    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        load messages
        """

        # validate
        req_slz = ListMessageChangeLogSerializer(data=request.query_params)
        req_slz.is_valid(raise_exception=True)
        req_data = req_slz.validated_data

        # load data
        logs = ChatMessageChangeLog.objects.filter(
            user=request.user,
            created_at=Subquery(
                ChatMessageChangeLog.objects.filter(message_id=OuterRef("message_id"), user=request.user)
                .order_by("-created_at")
                .values("created_at")[:1]
            ),
        ).order_by("created_at")
        if req_data.get("start_time"):
            logs = logs.filter(created_at__gt=req_data["start_time"])

        # page
        queryset = self.paginate_queryset(logs)

        # response
        resp_slz = MessageChangeLogSerializer(instance=queryset, many=True)
        return self.get_paginated_response(resp_slz.data)

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        save message
        """

        # validate request
        req_slz = CreateMessageChangeLogSerializer(data=request.data)
        req_slz.is_valid(raise_exception=True)
        req_data = req_slz.validated_data

        # save to db
        ChatMessageChangeLog.objects.create(
            user=request.user,
            message_id=req_data["message_id"],
            action=req_data["action"],
            content=req_data["content"],
        )

        # response
        return Response()
