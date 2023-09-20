from corsheaders.middleware import ACCESS_CONTROL_ALLOW_ORIGIN
from django.conf import settings
from django.http import StreamingHttpResponse
from ovinc_client.core.viewsets import CreateMixin, ListMixin, MainViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.chat.client import HunYuanClient, OpenAIClient
from apps.chat.constants import OpenAIModel
from apps.chat.models import ChatLog, ModelPermission
from apps.chat.permissions import AIModelPermission
from apps.chat.serializers import (
    CheckModelPermissionSerializer,
    OpenAIRequestSerializer,
)


class ChatViewSet(CreateMixin, MainViewSet):
    """
    Chat
    """

    queryset = ChatLog.objects.all()
    permission_classes = [AIModelPermission]

    def create(self, request, *args, **kwargs):
        """
        Create Chat
        """

        # validate request
        request_serializer = OpenAIRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # call api
        if request_data["model"] == OpenAIModel.HUNYUAN:
            streaming_content = HunYuanClient(request=request, **request_data).chat()
        else:
            streaming_content = OpenAIClient(request=request, **request_data).chat()

        # response
        return StreamingHttpResponse(
            streaming_content=streaming_content,
            headers={
                ACCESS_CONTROL_ALLOW_ORIGIN: settings.FRONTEND_URL,
                "Trace-ID": getattr(request, "otel_trace_id", ""),
            },
        )


class AIModelViewSet(ListMixin, MainViewSet):
    """
    Model
    """

    def list(self, reqeust, *args, **kwargs):
        """
        List Models
        """

        data = [
            {"id": model.model, "name": OpenAIModel.get_name(model.model)}
            for model in ModelPermission.authed_models(user=reqeust.user)
        ]
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
