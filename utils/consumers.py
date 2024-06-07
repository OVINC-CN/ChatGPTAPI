from channels.generic.websocket import AsyncWebsocketConsumer as _AsyncWebsocketConsumer

from utils.connections import connections_handler


class AsyncWebsocketConsumer(_AsyncWebsocketConsumer):
    async def connect(self):
        await super().connect()
        connections_handler.add_connection(self.channel_name, self.scope["client"][0])

    async def disconnect(self, code):
        await super().disconnect(code)
        connections_handler.remove_connection(self.channel_name, self.scope["client"][0])
