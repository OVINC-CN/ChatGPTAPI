import json
import time
from typing import Type

from asgiref.sync import async_to_sync
from autobahn.exception import Disconnected
from channels.exceptions import ChannelFull
from channels.layers import get_channel_layer
from channels_redis.core import RedisChannelLayer
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from ovinc_client.core.logger import logger

from apps.chat.client import MidjourneyClient, OpenAIClient
from apps.chat.client.base import BaseClient
from apps.chat.constants import WS_CLOSED_KEY, AIModelProvider
from apps.chat.exceptions import UnexpectedProvider, VerifyFailed
from apps.chat.models import AIModel, ChatRequest
from apps.chat.utils import format_error


class AsyncConsumer:
    """
    Async Consumer
    """

    def __init__(self, channel_name: str, key: str):
        self.channel_layer: RedisChannelLayer = get_channel_layer()
        self.channel_name = channel_name
        self.key = key

    def chat(self) -> None:
        try:
            is_closed = self.do_chat()
            if is_closed:
                return
            self.send(text_data=json.dumps({"is_finished": True}, ensure_ascii=False))
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[ChatError] %s", err)
            self.send(text_data=json.dumps({"data": format_error(err), "is_finished": True}, ensure_ascii=False))
        self.close()

    def send(self, text_data: str):
        async_to_sync(self.channel_layer.send)(
            channel=self.channel_name,
            message={"type": "chat.send", "text_data": text_data},
        )

    def close(self):
        async_to_sync(self.channel_layer.send)(
            channel=self.channel_name,
            message={
                "type": "chat.close",
            },
        )

    def do_chat(self) -> bool:
        # cache
        request_data = self.load_data_from_cache(self.key)

        # model
        model = self.get_model_inst(request_data.model)

        # get client
        client = self.get_model_client(model)

        # check closed
        if cache.get(WS_CLOSED_KEY.format(self.channel_name)):
            logger.warning("[ConnectClosedBeforeReplyStart] %s %s", self.channel_name, request_data.user)
            return True

        # init client
        client = client(
            user=request_data.user,
            model=request_data.model,
            messages=request_data.messages,
        )

        # response
        is_closed = False
        for data in client.chat():
            if is_closed:
                continue
            retry_times = 0
            while retry_times <= settings.CHANNEL_RETRY_TIMES:
                try:
                    self.send(
                        text_data=json.dumps(
                            {"data": data, "is_finished": False, "log_id": client.log.id}, ensure_ascii=False
                        )
                    )
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
                    time.sleep(settings.CHANNEL_RETRY_SLEEP)
                retry_times += 1

        return is_closed

    def load_data_from_cache(self, key: str) -> ChatRequest:
        request_data = cache.get(key=key)
        cache.delete(key=key)
        if not request_data:
            raise VerifyFailed()
        return ChatRequest(**request_data)

    def get_model_inst(self, model: str) -> AIModel:
        return get_object_or_404(AIModel, model=model)

    # pylint: disable=R0911
    def get_model_client(self, model: AIModel) -> Type[BaseClient]:
        match model.provider:
            case AIModelProvider.OPENAI:
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

    def send(self, text_data: str):
        self.message += json.loads(text_data).get("data", "")

    def close(self):
        return
