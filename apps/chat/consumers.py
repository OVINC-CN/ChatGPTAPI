import asyncio
import json
from typing import Type

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django_redis.client import DefaultClient
from ovinc_client.account.models import User
from ovinc_client.core.logger import logger

from apps.chat.client import (
    BaiLianClient,
    GeminiClient,
    HunYuanClient,
    OpenAIClient,
    OpenAIVisionClient,
    QianfanClient,
)
from apps.chat.client.base import BaseClient
from apps.chat.constants import AIModelProvider
from apps.chat.exceptions import UnexpectedProvider, VerifyFailed
from apps.chat.models import AIModel
from apps.chat.serializers import OpenAIChatRequestSerializer
from utils.consumers import AsyncWebsocketConsumer

cache: DefaultClient
USER_MODEL: User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data=None, *args, **kwargs):
        try:
            await self.chat(text_data=text_data)
            await self.send(text_data=json.dumps({"is_finished": True}, ensure_ascii=False))
            await asyncio.sleep(0)
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[ChatError] %s", err)
            await self.send(text_data=json.dumps({"data": str(err), "is_finished": True}, ensure_ascii=False))
            await asyncio.sleep(0)

    async def chat(self, text_data) -> None:
        # validate
        validated_data = self.validate_input(text_data=text_data)
        key = validated_data["key"]

        # cache
        request_data = self.load_data_from_cache(key)

        # model
        model = await sync_to_async(self.get_model_inst)(request_data["model"])

        # get client
        client = self.get_model_client(model)

        # init client
        client = await sync_to_async(client)(**request_data)

        # response
        async for data in client.chat():
            await self.send(
                text_data=json.dumps({"data": data, "is_finished": False, "log_id": client.log.id}, ensure_ascii=False)
            )
            await asyncio.sleep(0)

    def validate_input(self, text_data: str) -> dict:
        # json
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as err:
            raise VerifyFailed() from err

        # validate request
        request_serializer = OpenAIChatRequestSerializer(data=data)
        request_serializer.is_valid(raise_exception=True)
        return request_serializer.validated_data

    def load_data_from_cache(self, key: str) -> dict:
        request_data = cache.get(key=key)
        cache.delete(key=key)
        if not request_data:
            raise VerifyFailed()
        return request_data

    def get_model_inst(self, model: str) -> AIModel:
        return get_object_or_404(AIModel, model=model)

    def get_model_client(self, model: AIModel) -> Type[BaseClient]:
        match model.provider:
            case AIModelProvider.TENCENT:
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
            case _:
                raise UnexpectedProvider()
