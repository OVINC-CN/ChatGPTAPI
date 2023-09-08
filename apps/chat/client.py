import abc
import datetime
from typing import List

import openai
import tiktoken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from openai.openai_object import OpenAIObject
from rest_framework.request import Request

from apps.chat.constants import OpenAIUnitPrice
from apps.chat.models import ChatLog, Message
from core.renderers import APIRenderer

USER_MODEL = get_user_model()


class BaseClient:
    """
    Base Client for Chat
    """

    def __init__(self, request: Request, model: str, messages: List[Message], temperature: float, top_p: float):
        self.log: ChatLog = None
        self.request: Request = request
        self.user: USER_MODEL = request.user
        self.model: str = model
        self.messages: List[Message] = messages
        self.temperature: float = temperature
        self.top_p: float = top_p
        self.created_at: int = int()
        self.finished_at: int = int()

    @abc.abstractmethod
    def chat(self, *args, **kwargs) -> any:
        """
        Chat
        """

        raise NotImplementedError()

    @abc.abstractmethod
    def record(self, *args, **kwargs) -> None:
        """
        Record Log
        """

        raise NotImplementedError()


class OpenAIClient(BaseClient):
    """
    OpenAI Client
    """

    @transaction.atomic()
    def chat(self) -> any:
        self.created_at = int(datetime.datetime.now().timestamp() * 1000)
        response = openai.ChatCompletion.create(
            api_base=settings.OPENAI_API_BASE,
            api_key=settings.OPENAI_API_KEY,
            model=self.model,
            messages=self.messages,
            temperature=self.temperature,
            top_p=self.top_p,
            stream=True,
        )
        for chunk in response:
            self.record(response=chunk)
            yield APIRenderer().render(
                data={"content": response.choices[0].delta.get("content", "")},
                renderer_context={"request": self.request},
            )
        self.finished_at = int(datetime.datetime.now().timestamp() * 1000)
        self.post_chat()

    def record(self, *, response: OpenAIObject) -> None:
        # check log exist
        if self.log:
            self.log.content += response.choices[0].delta.get("content", "")
            return
        # create log
        self.log = ChatLog.objects.create(
            chat_id=response.id,
            user=self.user,
            model=self.model,
            messages=self.messages,
            content="",
            created_at=self.created_at,
        )
        return self.record(response=response)

    def post_chat(self) -> None:
        if not self.log:
            return
            # calculate tokens
        encoding = tiktoken.encoding_for_model(self.model)
        self.log.prompt_tokens = len(encoding.encode("".join([message["content"] for message in self.log.messages])))
        self.log.completion_tokens = len(encoding.encode(self.log.content))
        # calculate price
        price = OpenAIUnitPrice.get_price(self.model)
        self.log.prompt_token_unit_price = price.prompt_token_unit_price
        self.log.completion_token_unit_price = price.completion_token_unit_price
        # save
        self.log.finished_at = self.finished_at
        self.log.save()
