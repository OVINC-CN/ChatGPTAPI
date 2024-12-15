# pylint: disable=R0801

import abc
import uuid
from typing import List, Optional
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone
from httpx import AsyncClient, Client
from openai import OpenAI
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

    # pylint: disable=R0913,R0917
    def __init__(self, user: str, model: str, messages: List[dict], temperature: float, top_p: float):
        super().__init__(user=user, model=model, messages=messages, temperature=temperature, top_p=top_p)
        self.client = OpenAI(
            api_key=self.model_settings.get("api_key", settings.OPENAI_API_KEY),
            base_url=self.model_settings.get("base_url", settings.OPENAI_API_BASE),
            http_client=Client(proxy=settings.OPENAI_HTTP_PROXY_URL) if settings.OPENAI_HTTP_PROXY_URL else None,
        )


class OpenAIClient(OpenAIMixin, BaseClient):
    """
    OpenAI Client
    """

    async def _chat(self, *args, **kwargs) -> any:
        try:
            response = self.client.chat.completions.create(
                model=self.model.replace(".", ""),
                messages=self.messages,
                temperature=self.temperature,
                top_p=self.top_p,
                stream=True,
                timeout=settings.OPENAI_CHAT_TIMEOUT,
                stream_options={"include_usage": True},
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
            self.log.chat_id = chunk.id
            if chunk.choices:
                content += chunk.choices[0].delta.content or ""
                yield chunk.choices[0].delta.content or ""
            if chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens = chunk.usage.completion_tokens
        self.finished_at = int(timezone.now().timestamp() * 1000)
        await self.record(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)


class OpenAIVisionClient(OpenAIMixin, BaseClient):
    """
    OpenAI Vision Client
    """

    async def _chat(self, *args, **kwargs) -> any:
        try:
            # noinspection PyTypeChecker
            response = self.client.images.generate(
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
        # record
        await self.record(completion_tokens=1)
        # image
        if not settings.ENABLE_IMAGE_PROXY:
            yield f"![{self.messages[-1]['content']}]({response.data[0].url})"
        httpx_client = AsyncClient(http2=True, proxy=settings.OPENAI_HTTP_PROXY_URL)
        image_resp = await httpx_client.get(response.data[0].url)
        await httpx_client.aclose()
        if image_resp.status_code != status.HTTP_200_OK:
            raise LoadImageFailed()
        url = await COSClient().put_object(
            file=image_resp.content,
            file_name=f"{uuid.uuid4().hex}.{urlparse(response.data[0].url).path.split('.')[-1]}",
        )
        yield f"![output]({TCloudUrlParser(url).url})"
