import abc
import base64
import datetime
import hashlib
import hmac
import json
from typing import List, Union

import google.generativeai as genai
import qianfan
import requests
import tiktoken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from google.generativeai.types import GenerateContentResponse
from openai import AzureOpenAI
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.images_response import ImagesResponse
from qianfan import QfMessages, QfResponse
from requests import Response
from rest_framework.request import Request

from apps.chat.constants import (
    AI_API_REQUEST_TIMEOUT,
    HUNYUAN_DATA_PATTERN,
    GeminiRole,
    OpenAIRole,
)
from apps.chat.exceptions import UnexpectedError
from apps.chat.models import AIModel, ChatLog, HunYuanChuck, Message

USER_MODEL = get_user_model()


# pylint: disable=R0902
class BaseClient:
    """
    Base Client for Chat
    """

    # pylint: disable=R0913
    def __init__(
        self, request: Request, model: str, messages: Union[List[Message], QfMessages], temperature: float, top_p: float
    ):
        self.log: ChatLog = None
        self.request: Request = request
        self.user: USER_MODEL = request.user
        self.model: str = model
        self.model_inst: AIModel = AIModel.objects.get(model=model, is_enabled=True)
        self.messages: Union[List[Message], QfMessages] = messages
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
    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
        client = AzureOpenAI(
            api_key=settings.OPENAI_API_KEY,
            api_version="2023-05-15",
            azure_endpoint=settings.OPENAI_API_BASE,
        )
        response = client.chat.completions.create(
            model=self.model.replace(".", ""),
            messages=self.messages,
            temperature=self.temperature,
            top_p=self.top_p,
            stream=True,
        )
        # pylint: disable=E1133
        for chunk in response:
            self.record(response=chunk)
            yield chunk.choices[0].delta.content or ""
        self.finished_at = int(timezone.now().timestamp() * 1000)
        self.post_chat()

    # pylint: disable=W0221,R1710
    def record(self, response: ChatCompletionChunk, **kwargs) -> None:
        # check log exist
        if self.log:
            self.log.content += response.choices[0].delta.content or ""
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
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.currency_unit = self.model_inst.currency_unit
        # save
        self.log.finished_at = self.finished_at
        self.log.save()
        self.log.remove_content()


class OpenAIVisionClient(BaseClient):
    """
    OpenAI Vision Client
    """

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
        client = AzureOpenAI(
            api_key=settings.OPENAI_API_KEY,
            api_version="2023-12-01-preview",
            azure_endpoint=settings.OPENAI_API_BASE,
        )
        response = client.images.generate(
            model=self.model.replace(".", ""),
            prompt=self.messages[-1]["content"],
            n=1,
            size=self.model_inst.vision_size,
            quality=self.model_inst.vision_quality,
            style=self.model_inst.vision_style,
        )
        self.record(response=response)
        return f"![{self.messages[-1]['content']}]({response.data[0].url})"

    # pylint: disable=W0221,R1710
    def record(self, response: ImagesResponse, **kwargs) -> None:
        self.log = ChatLog.objects.create(
            user=self.user,
            model=self.model,
            messages=self.messages,
            content=response.data[0].url,
            completion_tokens=1,
            completion_token_unit_price=self.model_inst.completion_price,
            currency_unit=self.model_inst.currency_unit,
            created_at=self.created_at,
            finished_at=int(timezone.now().timestamp() * 1000),
        )
        self.log.remove_content()


class HunYuanClient(BaseClient):
    """
    Hun Yuan
    """

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        # log
        self.created_at = int(timezone.now().timestamp() * 1000)
        # call hunyuan api
        response = self.call_api()
        # explain completion
        completion_text = bytes()
        for chunk in response:
            completion_text += chunk
            # match hunyuan data content
            match = HUNYUAN_DATA_PATTERN.search(completion_text)
            if match is None:
                continue
            # load content
            resp_text = completion_text[match.regs[0][0] : match.regs[0][1]]
            completion_text = completion_text[match.regs[0][1] :]
            resp_text = json.loads(resp_text.decode()[6:])
            chunk = HunYuanChuck.create(resp_text)
            if chunk.error.code:
                raise UnexpectedError(detail=chunk.error.message)
            self.record(response=chunk)
            yield chunk.choices[0].delta.content
        if not self.log:
            return
        self.log.finished_at = int(timezone.now().timestamp() * 1000)
        self.log.save()
        self.log.remove_content()

    # pylint: disable=W0221,R1710
    def record(self, response: HunYuanChuck) -> None:
        # check log exist
        if self.log:
            self.log.content += response.choices[0].delta.content
            self.log.prompt_tokens = response.usage.prompt_tokens
            self.log.completion_tokens = response.usage.completion_tokens
            self.log.prompt_token_unit_price = self.model_inst.prompt_price
            self.log.completion_token_unit_price = self.model_inst.completion_price
            self.log.currency_unit = self.model_inst.currency_unit
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

    def call_api(self) -> Response:
        data = {
            "app_id": settings.QCLOUD_APP_ID,
            "secret_id": settings.QCLOUD_SECRET_ID,
            "timestamp": int(timezone.now().timestamp()),
            "expired": int((timezone.now() + datetime.timedelta(minutes=5)).timestamp()),
            "messages": self.messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "stream": 1,
        }
        message_string = ",".join(
            [f"{{\"role\":\"{message['role']}\",\"content\":\"{message['content']}\"}}" for message in self.messages]
        )
        message_string = f"[{message_string}]"
        params = {**data, "messages": message_string}
        params = dict(sorted(params.items(), key=lambda x: x[0]))
        url = (
            settings.QCLOUD_HUNYUAN_API_URL.split("://", 1)[1]
            + "?"
            + "&".join([f"{key}={val}" for key, val in params.items()])
        )
        signature = hmac.new(settings.QCLOUD_SECRET_KEY.encode(), url.encode(), hashlib.sha1).digest()
        encoded_signature = base64.b64encode(signature).decode()
        headers = {"Authorization": encoded_signature}
        resp = requests.post(
            settings.QCLOUD_HUNYUAN_API_URL, json=data, headers=headers, stream=True, timeout=AI_API_REQUEST_TIMEOUT
        )
        return resp


class GeminiClient(BaseClient):
    """
    Gemini Pro
    """

    # pylint: disable=R0913
    def __init__(self, request: Request, model: str, messages: List[Message], temperature: float, top_p: float):
        super().__init__(request=request, model=model, messages=messages, temperature=temperature, top_p=top_p)
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.genai_model = genai.GenerativeModel("gemini-pro")

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
        response = self.genai_model.generate_content(
            contents=[
                {"role": self.get_role(message["role"]), "parts": [message["content"]]} for message in self.messages
            ],
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
                top_p=self.top_p,
            ),
            stream=True,
        )
        for chunk in response:
            self.record(response=chunk)
            yield chunk.text
        self.finished_at = int(timezone.now().timestamp() * 1000)
        self.post_chat()

    @classmethod
    def get_role(cls, role: str) -> str:
        if role == OpenAIRole.ASSISTANT:
            return GeminiRole.MODEL
        return GeminiRole.USER

    # pylint: disable=W0221,R1710
    def record(self, response: GenerateContentResponse, **kwargs) -> None:
        # check log exist
        if self.log:
            self.log.content += response.text
            return
        # create log
        self.log = ChatLog.objects.create(
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
        # calculate characters
        self.log.prompt_tokens = len("".join([message["content"] for message in self.log.messages]))
        self.log.completion_tokens = len(self.log.content)
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.currency_unit = self.model_inst.currency_unit
        # save
        self.log.finished_at = self.finished_at
        self.log.save()
        self.log.remove_content()


class QianfanClient(BaseClient):
    """
    Baidu Qianfan
    """

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
        client = qianfan.ChatCompletion(ak=settings.QIANFAN_ACCESS_KEY, sk=settings.QIANFAN_SECRET_KEY)
        response = client.do(
            model=self.model,
            messages=self.messages,
            temperature=self.temperature,
            top_p=self.top_p,
            stream=True,
        )
        for chunk in response:
            self.record(response=chunk)
            yield chunk.body.get("result", "")
        self.finished_at = int(timezone.now().timestamp() * 1000)
        self.post_chat()

    # pylint: disable=W0221,R1710
    def record(self, response: QfResponse, **kwargs) -> None:
        # check log exist
        if self.log:
            self.log.content += response.body.get("result", "")
            usage = response.body.get("usage", {})
            self.log.prompt_tokens = usage.get("prompt_tokens", 0)
            self.log.completion_tokens = usage.get("completion_tokens", 0)
            return
        # create log
        self.log = ChatLog.objects.create(
            chat_id=response.body.get("id", ""),
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
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.currency_unit = self.model_inst.currency_unit
        # save
        self.log.finished_at = self.finished_at
        self.log.save()
        self.log.remove_content()
