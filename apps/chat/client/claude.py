import base64
from typing import List

from anthropic import Anthropic
from anthropic.types import (
    RawContentBlockDeltaEvent,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
)
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext
from httpx import Client
from ovinc_client.core.logger import logger

from apps.chat.client.base import BaseClient
from apps.chat.constants import ClaudeMessageType, MessageContentType, OpenAIRole
from apps.chat.exceptions import FileExtractFailed, GenerateFailed


class ClaudeClient(BaseClient):
    """
    Claude Client
    """

    async def chat(self, *args, **kwargs) -> any:
        client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL,
            http_client=Client(proxy=settings.OPENAI_HTTP_PROXY_URL) if settings.OPENAI_HTTP_PROXY_URL else None,
        )
        system, messages = self.parse_messages()
        try:
            response = client.messages.create(
                max_tokens=settings.ANTHROPIC_MAX_TOKENS,
                system=system,
                messages=messages,
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
                stream=True,
            )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        input_tokens = 0
        output_tokens = 0
        # pylint: disable=E1133
        for chunk in response:
            match chunk.type:
                case ClaudeMessageType.MESSAGE_START:
                    chunk: RawMessageStartEvent
                    input_tokens = chunk.message.usage.input_tokens
                    self.record(chunk=chunk)
                case ClaudeMessageType.MESSAGE_DELTA:
                    chunk: RawMessageDeltaEvent
                    output_tokens = chunk.usage.output_tokens
                case ClaudeMessageType.CONTENT_BLOCK_DELTA:
                    chunk: RawContentBlockDeltaEvent
                    yield chunk.delta.text
        self.finished_at = int(timezone.now().timestamp() * 1000)
        await self.post_chat(input_tokens=input_tokens, output_tokens=output_tokens)

    def parse_messages(self) -> (str, List[dict]):
        # parse image
        for message in self.messages:
            if not isinstance(message["content"], list):
                continue
            for index, content in enumerate(message["content"]):
                if content.get("type") != MessageContentType.IMAGE_URL:
                    continue
                image_data = self.convert_url_to_base64(content["image_url"]["url"])
                message["content"][index] = {
                    "type": MessageContentType.IMAGE,
                    "source": {
                        "type": "base64",
                        "media_type": "image/webp",
                        "data": image_data,
                    },
                }
        # parse system
        system = ""
        if self.messages[0]["role"] == OpenAIRole.SYSTEM:
            system = self.messages[0]["content"]
            return system, self.messages[1:]
        return system, self.messages

    def convert_url_to_base64(self, url: str) -> str:
        with Client(http2=True) as client:
            response = client.get(url)
            if response.status_code == 200:
                return base64.b64encode(response.content).decode()
            raise FileExtractFailed(gettext("Parse Image To Base64 Failed"))

    # pylint: disable=W0221
    def record(self, chunk, *args, **kwargs) -> None:
        self.log.chat_id = chunk.message.id

    async def post_chat(self, input_tokens: int, output_tokens: int) -> None:
        if not self.log:
            return
        # calculate characters
        self.log.prompt_tokens = input_tokens
        self.log.completion_tokens = output_tokens
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        # save
        self.log.finished_at = self.finished_at
        await database_sync_to_async(self.log.save)()
