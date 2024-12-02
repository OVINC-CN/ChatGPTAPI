# pylint: disable=R0801
import abc
import uuid
from typing import Optional
from urllib.parse import urlparse

import httpx
import tiktoken
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from httpx import Client
from openai import OpenAI
from openai.types import ImagesResponse
from openai.types.chat import ChatCompletionChunk
from ovinc_client.core.logger import logger
from rest_framework import status

from apps.chat.client.base import BaseClient
from apps.chat.exceptions import GenerateFailed, LoadImageFailed
from apps.cos.client import COSClient
from apps.cos.utils import TCloudUrlParser


class OpenAIMixin(abc.ABC):
    """
    OpenAI Mixin
    """

    model_settings: Optional[dict]

    def build_client(self, api_version: str) -> OpenAI:
        return OpenAI(
            api_key=self.model_settings.get("api_key", settings.OPENAI_API_KEY),
            base_url=self.model_settings.get("base_url", settings.OPENAI_API_BASE),
            http_client=Client(proxy=settings.OPENAI_HTTP_PROXY_URL) if settings.OPENAI_HTTP_PROXY_URL else None,
        )


class OpenAIClient(OpenAIMixin, BaseClient):
    """
    OpenAI Client
    """

    async def chat(self, *args, **kwargs) -> any:
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
        content = ""
        prompt_tokens = 0
        completion_tokens = 0
        # pylint: disable=E1133
        for chunk in response:
            self.record(response=chunk)
            if chunk.choices:
                content += chunk.choices[0].delta.content or ""
                yield chunk.choices[0].delta.content or ""
            elif chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens = chunk.usage.completion_tokens
        self.finished_at = int(timezone.now().timestamp() * 1000)
        await self.post_chat(content, prompt_tokens, completion_tokens)

    # pylint: disable=W0221,R1710
    def record(self, response: ChatCompletionChunk, **kwargs) -> None:
        self.log.chat_id = response.id

    async def post_chat(self, content: str, prompt_tokens: int, completion_tokens: int) -> None:
        if not self.log:
            return
        # calculate tokens
        if prompt_tokens and completion_tokens:
            self.log.prompt_tokens = prompt_tokens
            self.log.completion_tokens = completion_tokens
        else:
            encoding = tiktoken.encoding_for_model(self.model)
            self.log.prompt_tokens = len(encoding.encode("".join([message["content"] for message in self.messages])))
            self.log.completion_tokens = len(encoding.encode(content))
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        # save
        self.log.finished_at = self.finished_at
        await database_sync_to_async(self.log.save)()


class OpenAIVisionClient(OpenAIMixin, BaseClient):
    """
    OpenAI Vision Client
    """

    async def chat(self, *args, **kwargs) -> any:
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
        await self.record(response=response)
        if not settings.ENABLE_IMAGE_PROXY:
            yield f"![{self.messages[-1]['content']}]({response.data[0].url})"
        httpx_client = httpx.AsyncClient(http2=True, proxy=settings.OPENAI_HTTP_PROXY_URL)
        image_resp = await httpx_client.get(response.data[0].url)
        await httpx_client.aclose()
        if image_resp.status_code != status.HTTP_200_OK:
            raise LoadImageFailed()
        url = await COSClient().put_object(
            file=image_resp.content,
            file_name=f"{uuid.uuid4().hex}.{urlparse(response.data[0].url).path.split('.')[-1]}",
        )
        yield f"![output]({TCloudUrlParser(url).url})"

    # pylint: disable=W0221,R1710,W0236
    async def record(self, response: ImagesResponse, **kwargs) -> None:
        self.log.completion_tokens = 1
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.finished_at = int(timezone.now().timestamp() * 1000)
        await database_sync_to_async(self.log.save)()
