from channels.generic.websocket import AsyncWebsocketConsumer as _AsyncWebsocketConsumer
from django.conf import settings
from django.core.cache import cache

from apps.chat.constants import WS_CLOSED_KEY
from utils.connections import connections_handler


class AsyncWebsocketConsumer(_AsyncWebsocketConsumer):
    async def connect(self):
        await super().connect()
        connections_handler.add_connection(self.channel_name, self.scope["client"][0])

    async def disconnect(self, code):
        cache.set(key=WS_CLOSED_KEY.format(self.channel_name), value=True, timeout=settings.CHANNEL_CLOSE_KEY_TIMEOUT)
        await super().disconnect(code)
        connections_handler.remove_connection(self.channel_name, self.scope["client"][0])
