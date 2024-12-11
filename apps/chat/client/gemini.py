# pylint: disable=R0801

import base64
from typing import List

import google.generativeai as genai
import httpx
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext
from httpx import Client
from openai import OpenAI
from openai.types.chat import ChatCompletionChunk
from ovinc_client.core.logger import logger

from apps.chat.client.base import BaseClient
from apps.chat.constants import MessageContentType
from apps.chat.exceptions import FileExtractFailed, GenerateFailed
from apps.chat.models import Message


class GeminiClient(BaseClient):
    """
    Gemini Client
    """

    # pylint: disable=R0913,R0917
    def __init__(self, user: str, model: str, messages: List[Message], temperature: float, top_p: float):
        super().__init__(user=user, model=model, messages=messages, temperature=temperature, top_p=top_p)
        self.client = OpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.GEMINI_API_URL,
            http_client=Client(proxy=settings.OPENAI_HTTP_PROXY_URL) if settings.OPENAI_HTTP_PROXY_URL else None,
        )
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.genai_model = genai.GenerativeModel(self.model)
        self.post_init()

    def post_init(self) -> None:
        for message in self.messages:
            if not isinstance(message["content"], list):
                continue
            for content in message["content"]:
                if content.get("type") != MessageContentType.IMAGE_URL:
                    continue
                content["image_url"]["url"] = self.convert_url_to_base64(content["image_url"]["url"])

    async def chat(self, *args, **kwargs) -> any:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
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
        # pylint: disable=E1133
        for chunk in response:
            self.record(response=chunk)
            content += chunk.choices[0].delta.content or ""
            yield chunk.choices[0].delta.content or ""
        self.finished_at = int(timezone.now().timestamp() * 1000)
        await self.post_chat(content=content)

    # pylint: disable=W0221,R1710
    def record(self, response: ChatCompletionChunk, **kwargs) -> None:
        pass

    async def post_chat(self, content: str) -> None:
        if not self.log:
            return
        # calculate characters
        self.log.prompt_tokens = self.genai_model.count_tokens(self.parse_messages()).total_tokens
        self.log.completion_tokens = self.genai_model.count_tokens(content).total_tokens
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        # save
        self.log.finished_at = self.finished_at
        await database_sync_to_async(self.log.save)()

    def convert_url_to_base64(self, url: str) -> str:
        with httpx.Client(http2=True) as client:
            response = client.get(url)
            if response.status_code == 200:
                return f"data:image/jpeg;base64,{base64.b64encode(response.content).decode()}"
            raise FileExtractFailed(gettext("Parse Image To Base64 Failed"))

    def parse_messages(self) -> str:
        data = ""
        for message in self.messages:
            if isinstance(message["content"], list):
                for content in message["content"]:
                    if content.get("type") == MessageContentType.IMAGE_URL:
                        continue
                    data += str(content["text"])
                continue
            data += str(message["content"])
        return data
