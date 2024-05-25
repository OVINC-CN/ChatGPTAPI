# pylint: disable=R0801
import abc
import uuid
from typing import Optional
from urllib.parse import urlparse

import httpx
import tiktoken
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from httpx import Client
from openai import AzureOpenAI
from openai.types import ImagesResponse
from openai.types.chat import ChatCompletionChunk
from ovinc_client.core.logger import logger
from rest_framework import status

from apps.chat.client.base import BaseClient
from apps.chat.exceptions import GenerateFailed, LoadImageFailed
from apps.chat.models import ChatLog
from utils.cos import cos_client


class OpenAIMixin(abc.ABC):
    """
    OpenAI Mixin
    """

    model_settings: Optional[dict]

    def build_client(self, api_version: str) -> AzureOpenAI:
        return AzureOpenAI(
            api_key=self.model_settings.get("api_key", settings.OPENAI_API_KEY),
            api_version=api_version,
            azure_endpoint=self.model_settings.get("endpoint", settings.OPENAI_API_BASE),
            http_client=Client(proxy=settings.OPENAI_HTTP_PROXY_URL) if settings.OPENAI_HTTP_PROXY_URL else None,
        )


class OpenAIClient(OpenAIMixin, BaseClient):
    """
    OpenAI Client
    """

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
        client = self.build_client(api_version="2023-05-15")
        try:
            response = client.chat.completions.create(
                model=self.model.replace(".", ""),
                messages=self.messages,
                temperature=self.temperature,
                top_p=self.top_p,
                stream=True,
            )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
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


class OpenAIVisionClient(OpenAIMixin, BaseClient):
    """
    OpenAI Vision Client
    """

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
        client = self.build_client(api_version="2023-12-01-preview")
        try:
            response = client.images.generate(
                model=self.model.replace(".", ""),
                prompt=self.messages[-1]["content"],
                n=1,
                size=self.model_inst.vision_size,
                quality=self.model_inst.vision_quality,
                style=self.model_inst.vision_style,
            )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            return
        self.record(response=response)
        if not settings.ENABLE_IMAGE_PROXY:
            yield f"![{self.messages[-1]['content']}]({response.data[0].url})"
        httpx_client = httpx.Client(http2=True, proxy=settings.OPENAI_HTTP_PROXY_URL)
        image_resp = httpx_client.get(response.data[0].url)
        if image_resp.status_code != status.HTTP_200_OK:
            raise LoadImageFailed()
        url = cos_client.put_object(
            file=image_resp.content,
            file_name=f"{uuid.uuid4().hex}.{urlparse(response.data[0].url).path.split('.')[-1]}",
        )
        yield f"![{self.messages[-1]['content']}]({url})"

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
