from corsheaders.middleware import ACCESS_CONTROL_ALLOW_ORIGIN
from django.conf import settings
from django.core.cache import cache
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from ovinc_client.core.utils import uniq_id
from ovinc_client.core.viewsets import CreateMixin, ListMixin, MainViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.chat.client import GeminiClient, HunYuanClient, OpenAIClient, QianfanClient
from apps.chat.constants import AIModelProvider
from apps.chat.exceptions import UnexpectedProvider, VerifyFailed
from apps.chat.models import AIModel, ChatLog, ModelPermission
from apps.chat.permissions import AIModelPermission
from apps.chat.serializers import (
    CheckModelPermissionSerializer,
    OpenAIChatRequestSerializer,
    OpenAIRequestSerializer,
)


# pylint: disable=R0901
class ChatViewSet(CreateMixin, MainViewSet):
    """
    Chat
    """

    queryset = ChatLog.objects.all()

    def create(self, request, *args, **kwargs):
        """
        Create Chat
        """

        # validate request
        request_serializer = OpenAIChatRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        key = request_serializer.validated_data["key"]

        # cache
        request_data = cache.get(key=key)
        cache.delete(key=key)
        if not request_data:
            raise VerifyFailed()

        # model
        model: AIModel = get_object_or_404(AIModel, model=request_data["model"])

        # call api
        match model.provider:
            case AIModelProvider.TENCENT:
                streaming_content = HunYuanClient(request=request, **request_data).chat()
            case AIModelProvider.GOOGLE:
                streaming_content = GeminiClient(request=request, **request_data).chat()
            case AIModelProvider.BAIDU:
                streaming_content = QianfanClient(request=request, **request_data).chat()
            case AIModelProvider.OPENAI:
                streaming_content = OpenAIClient(request=request, **request_data).chat()
            case _:
                raise UnexpectedProvider()

        # response
        return StreamingHttpResponse(
            streaming_content=streaming_content,
            headers={
                ACCESS_CONTROL_ALLOW_ORIGIN: settings.FRONTEND_URL,
                "Trace-ID": getattr(request, "otel_trace_id", ""),
            },
        )

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
        cache.set(key=cache_key, value=request_data, timeout=settings.OPENAI_PRE_CHECK_TIMEOUT)

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
        data.sort(key=lambda model: model["id"])
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
