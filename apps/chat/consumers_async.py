import asyncio
import json
from typing import Type

from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels_redis.core import RedisChannelLayer
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django_redis.client import DefaultClient
from ovinc_client.account.models import User
from ovinc_client.core.logger import celery_logger

from apps.chat.client import (
    BaiLianClient,
    GeminiClient,
    HunYuanClient,
    HunYuanVisionClient,
    KimiClient,
    OpenAIClient,
    OpenAIVisionClient,
    QianfanClient,
)
from apps.chat.client.base import BaseClient
from apps.chat.constants import AIModelProvider
from apps.chat.exceptions import UnexpectedProvider, VerifyFailed
from apps.chat.models import AIModel

cache: DefaultClient
USER_MODEL: User = get_user_model()


class ChatAsyncConsumer:
    def __init__(self, channel_name: str):
        self.channel_name = channel_name
        self.channel_layer: RedisChannelLayer = get_channel_layer()
        celery_logger.info("[AsyncChatInited] %s", self.channel_name)

    async def receive(self, key: str):
        try:
            await self.chat(key=key)
            await self.send(text_data=json.dumps({"is_finished": True}, ensure_ascii=False))
            celery_logger.info("[ChatFinished] %s", self.channel_name)
        except Exception as err:  # pylint: disable=W0718
            celery_logger.exception("[ChatError] %s %s", self.channel_name, err)
            await self.send(text_data=json.dumps({"data": str(err), "is_finished": True}, ensure_ascii=False))
        await self.close()
        celery_logger.info("[ChannelClosed] %s", self.channel_name)

    async def send(self, text_data: str = None, bytes_data: bytes = None, close: bool = False) -> None:
        await self.channel_layer.send(
            self.channel_name,
            {"type": "send.message", "text_data": text_data, "bytes_data": bytes_data, "close": close},
        )

    async def close(self) -> None:
        await self.channel_layer.send(self.channel_name, {"type": "close.channel"})

    async def chat(self, key: str) -> None:
        # cache
        request_data = self.load_data_from_cache(key)

        # model
        model = await database_sync_to_async(self.get_model_inst)(request_data["model"])

        # get client
        client = self.get_model_client(model)

        # init client
        client = await database_sync_to_async(client)(**request_data)

        # response
        async for data in client.chat():
            await self.send(
                text_data=json.dumps({"data": data, "is_finished": False, "log_id": client.log.id}, ensure_ascii=False)
            )
            await asyncio.sleep(0)

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
            case AIModelProvider.BAIDU:
                return QianfanClient
            case AIModelProvider.OPENAI:
                if model.is_vision:
                    return OpenAIVisionClient
                return OpenAIClient
            case AIModelProvider.ALIYUN:
                return BaiLianClient
            case AIModelProvider.MOONSHOT:
                return KimiClient
            case _:
                raise UnexpectedProvider()
