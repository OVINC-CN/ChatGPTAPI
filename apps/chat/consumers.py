import json
import time
from typing import Type

from autobahn.exception import Disconnected
from channels.exceptions import ChannelFull
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django_redis.client import DefaultClient
from ovinc_client.account.models import User
from ovinc_client.core.logger import logger

from apps.chat.client import OpenAIClient
from apps.chat.client.base import BaseClient
from apps.chat.constants import WS_CLOSED_KEY, AIModelProvider
from apps.chat.exceptions import UnexpectedProvider, VerifyFailed
from apps.chat.models import AIModel, ChatRequest
from apps.chat.serializers import OpenAIChatRequestSerializer
from apps.chat.utils import format_error
from utils.consumers import WebsocketConsumer

USER_MODEL: User = get_user_model()
cache: DefaultClient


class ChatConsumer(WebsocketConsumer):
    def receive(self, text_data=None, *args, **kwargs):
        # load input
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as err:
            raise VerifyFailed() from err

        # validate request
        request_serializer = OpenAIChatRequestSerializer(data=data)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # async chat
        self.chat(request_data=self.load_data_from_cache(request_data["key"]))

    def chat_send(self, data: dict):
        self.send(text_data=json.dumps(data, ensure_ascii=False))

    def chat_close(self):
        self.close()

    def chat(self, request_data: ChatRequest) -> None:
        try:
            is_closed = self.inner_chat(request_data=request_data)
            if is_closed:
                return
            self.chat_send(data={"is_finished": True})
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[ChatError] %s", err)
            self.chat_send(data=format_error(log_id="", error=err))
        self.chat_close()

    def inner_chat(self, request_data: ChatRequest) -> bool:
        # model
        model = self.get_model_inst(request_data.model)
        # get client
        client = self.get_model_client(model)
        # check closed
        if cache.get(WS_CLOSED_KEY.format(self.channel_name)):
            logger.warning("[ConnectClosedBeforeReplyStart] %s %s", self.channel_name, request_data.user)
            return True
        # init client
        client = client(user=request_data.user, model=request_data.model, messages=request_data.messages)
        # response
        is_closed = False
        for data in client.chat():
            if is_closed:
                continue
            retry_times = 0
            while retry_times <= settings.CHANNEL_RETRY_TIMES:
                try:
                    self.chat_send(data)
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
            case _:
                raise UnexpectedProvider()


class JSONModeConsumer(ChatConsumer):
    """
    JSON Mode Consumer
    """

    def __init__(self, channel_name: str):
        super().__init__()
        self.message = ""
        self.channel_name = channel_name

    def chat_send(self, data: dict):
        self.message += data.get("data", "")

    def chat_close(self):
        return
