from channels.generic.websocket import WebsocketConsumer as _WebsocketConsumer
from django.conf import settings
from django.core.cache import cache

from apps.chat.constants import WS_CLOSED_KEY
from utils.connections import connections_handler


class WebsocketConsumer(_WebsocketConsumer):
    def connect(self):
        super().connect()
        connections_handler.add_connection(self.channel_name, self.scope["client"][0])

    def disconnect(self, code):
        cache.set(key=WS_CLOSED_KEY.format(self.channel_name), value=True, timeout=settings.CHANNEL_CLOSE_KEY_TIMEOUT)
        super().disconnect(code)
        connections_handler.remove_connection(self.channel_name, self.scope["client"][0])
