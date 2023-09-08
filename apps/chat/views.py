from django.http import StreamingHttpResponse

from apps.chat.client import OpenAIClient
from apps.chat.models import ChatLog
from apps.chat.serializers import OpenAIRequestSerializer
from core.viewsets import CreateMixin, MainViewSet


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
        request_serializer = OpenAIRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # call api
        streaming_content = OpenAIClient(request=request, **request_data).chat()

        # response
        return StreamingHttpResponse(streaming_content=streaming_content)
