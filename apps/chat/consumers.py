import json

from django.contrib.auth import get_user_model
from ovinc_client.account.models import User

from apps.cel.tasks import async_reply
from apps.chat.exceptions import VerifyFailed
from apps.chat.serializers import OpenAIChatRequestSerializer
from utils.consumers import AsyncWebsocketConsumer

USER_MODEL: User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data=None, *args, **kwargs):
        # load input
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as err:
            raise VerifyFailed() from err

        # validate request
        request_serializer = OpenAIChatRequestSerializer(data=data)
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data

        # async chat
        async_reply.apply_async(kwargs={"channel_name": self.channel_name, "key": data["key"]})
        async_reply.apply_async(kwargs={"channel_name": self.channel_name, "key": data["key"]})

    async def chat_send(self, event: dict):
        await self.send(text_data=event["text_data"])

    async def chat_close(self, event: dict):
        await self.close()

    async def disconnect(self, code):
        await super().disconnect(code)
