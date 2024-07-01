import json

from apps.cel.tasks.chat import do_chat
from apps.chat.exceptions import VerifyFailed
from apps.chat.serializers import OpenAIChatRequestSerializer
from utils.consumers import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data=None, *args, **kwargs):
        # json
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as err:
            raise VerifyFailed() from err

        # validate request
        request_serializer = OpenAIChatRequestSerializer(data=data)
        request_serializer.is_valid(raise_exception=True)
        validated_data = request_serializer.validated_data

        # async chat
        do_chat.delay(channel_name=self.channel_name, key=validated_data["key"])

    async def send_message(self, event: dict):
        await self.send(
            text_data=event.get("text_data", None),
            bytes_data=event.get("bytes_data", None),
            close=event.get("close", False),
        )

    async def close_channel(self, event: dict):
        await self.close(code=event.get("code", None), reason=event.get("reason", None))
