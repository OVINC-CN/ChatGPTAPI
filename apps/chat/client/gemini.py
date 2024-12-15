# pylint: disable=R0801

import base64
from typing import List

from django.conf import settings
from django.utils.translation import gettext
from httpx import Client
from openai import OpenAI
from ovinc_client.core.logger import logger

from apps.chat.client.openai import BaseClient
from apps.chat.constants import MessageContentType, SpanType
from apps.chat.exceptions import FileExtractFailed, GenerateFailed


class GeminiClient(BaseClient):
    """
    Gemini Client
    """

    # pylint: disable=R0913,R0917
    def __init__(self, user: str, model: str, messages: List[dict], temperature: float, top_p: float):
        super().__init__(user=user, model=model, messages=messages, temperature=temperature, top_p=top_p)
        self.client = OpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.GEMINI_API_URL,
            http_client=Client(proxy=settings.OPENAI_HTTP_PROXY_URL) if settings.OPENAI_HTTP_PROXY_URL else None,
        )
        self.post_init()

    def post_init(self) -> None:
        for message in self.messages:
            if not isinstance(message["content"], list):
                continue
            for content in message["content"]:
                if content.get("type") != MessageContentType.IMAGE_URL:
                    continue
                content["image_url"]["url"] = self.convert_url_to_base64(content["image_url"]["url"])

    async def _chat(self, *args, **kwargs) -> any:
        try:
            with self.tracer.start_as_current_span(SpanType.API):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stream=True,
                    timeout=settings.GEMINI_CHAT_TIMEOUT,
                    stream_options={"include_usage": True},
                )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        prompt_tokens = 0
        completion_tokens = 0
        with self.tracer.start_as_current_span(SpanType.CHUNK):
            # pylint: disable=E1133
            for chunk in response:
                if chunk.choices:
                    yield chunk.choices[0].delta.content or ""
                if chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens
        await self.record(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

    def convert_url_to_base64(self, url: str) -> str:
        with Client(http2=True) as client:
            response = client.get(url)
            if response.status_code == 200:
                return f"data:image/webp;base64,{base64.b64encode(response.content).decode()}"
            raise FileExtractFailed(gettext("Parse Image To Base64 Failed"))
