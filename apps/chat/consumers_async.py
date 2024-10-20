import asyncio
import json
from typing import Type

from autobahn.exception import Disconnected
from channels.db import database_sync_to_async
from channels.exceptions import ChannelFull
from channels.layers import get_channel_layer
from channels_redis.core import RedisChannelLayer
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from ovinc_client.core.logger import logger

from apps.chat.client import (
    GeminiClient,
    HunYuanClient,
    HunYuanVisionClient,
    MidjourneyClient,
    OpenAIClient,
    OpenAIVisionClient,
)
from apps.chat.client.base import BaseClient
from apps.chat.constants import WS_CLOSED_KEY, AIModelProvider
from apps.chat.exceptions import UnexpectedProvider, VerifyFailed
from apps.chat.models import AIModel


class AsyncConsumer:
    """
    Async Consumer
    """

    def __init__(self, channel_name: str, key: str):
        self.channel_layer: RedisChannelLayer = get_channel_layer()
        self.channel_name = channel_name
        self.key = key

    async def chat(self) -> None:
        try:
            is_closed = await self.do_chat()
            if is_closed:
                return
            await self.send(text_data=json.dumps({"is_finished": True}, ensure_ascii=False))
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[ChatError] %s", err)
            await self.send(text_data=json.dumps({"data": str(err), "is_finished": True}, ensure_ascii=False))
        await self.close()

    async def send(self, text_data: str):
        await self.channel_layer.send(
            channel=self.channel_name,
            message={"type": "chat.send", "text_data": text_data},
        )

    async def close(self):
        await self.channel_layer.send(
            channel=self.channel_name,
            message={
                "type": "chat.close",
            },
        )

    async def do_chat(self) -> bool:
        # cache
        request_data = self.load_data_from_cache(self.key)

        # model
        model = await database_sync_to_async(self.get_model_inst)(request_data["model"])

        # get client
        client = self.get_model_client(model)

        # init client
        client = await database_sync_to_async(client)(**request_data)

        # response
        is_closed = False
        async for data in client.chat():
            if is_closed:
                continue
            retry_times = 0
            while retry_times <= settings.CHANNEL_RETRY_TIMES:
                try:
                    await self.send(
                        text_data=json.dumps(
                            {"data": data, "is_finished": False, "log_id": client.log.id}, ensure_ascii=False
                        )
                    )
                    await asyncio.sleep(0)
                    break
                except Disconnected:
                    logger.warning("[SendMessageFailed-Disconnected] Channel: %s", self.channel_name)
                    is_closed = True
                    break
                except ChannelFull:
                    if cache.get(WS_CLOSED_KEY.format(self.channel_name)):
                        logger.warning("[SendMessageFailed-Disconnected] Channel: %s", self.channel_name)
                        is_closed = True
                        break
                    logger.warning(
                        "[SendMessageFailed-ChannelFull] Channel: %s; Retry: %d;", self.channel_name, retry_times
                    )
                    await asyncio.sleep(settings.CHANNEL_RETRY_SLEEP)
                retry_times += 1

        return is_closed

    def load_data_from_cache(self, key: str) -> dict:
        request_data = cache.get(key=key)
        cache.delete(key=key)
        if not request_data:
            raise VerifyFailed()
        return request_data

    def get_model_inst(self, model: str) -> AIModel:
        return get_object_or_404(AIModel, model=model)

    # pylint: disable=R0911
    def get_model_client(self, model: AIModel) -> Type[BaseClient]:
        match model.provider:
            case AIModelProvider.TENCENT:
                if model.is_vision:
                    return HunYuanVisionClient
                return HunYuanClient
            case AIModelProvider.GOOGLE:
                return GeminiClient
            case AIModelProvider.OPENAI:
                if model.is_vision:
                    return OpenAIVisionClient
                return OpenAIClient
            case AIModelProvider.MIDJOURNEY:
                return MidjourneyClient
            case _:
                raise UnexpectedProvider()


class JSONModeConsumer(AsyncConsumer):
    """
    JSON Mode Consumer
    """

    def __init__(self, key: str):
        super().__init__("", key)
        self.message = ""

    async def send(self, text_data: str):
        self.message += json.loads(text_data).get("data", "")

    async def close(self):
        return
