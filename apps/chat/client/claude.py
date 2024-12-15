import base64
from typing import List

from anthropic import Anthropic
from anthropic.types import (
    RawContentBlockDeltaEvent,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
)
from django.conf import settings
from django.utils.translation import gettext
from httpx import Client
from opentelemetry.trace import SpanKind
from ovinc_client.core.logger import logger

from apps.chat.client.base import BaseClient
from apps.chat.constants import (
    ClaudeMessageType,
    MessageContentType,
    OpenAIRole,
    SpanType,
)
from apps.chat.exceptions import FileExtractFailed, GenerateFailed


class ClaudeClient(BaseClient):
    """
    Claude Client
    """

    async def _chat(self, *args, **kwargs) -> any:
        client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL,
            http_client=Client(proxy=settings.OPENAI_HTTP_PROXY_URL) if settings.OPENAI_HTTP_PROXY_URL else None,
        )
        system, messages = self.parse_messages()
        try:
            with self.start_span(SpanType.API, SpanKind.CLIENT):
                response = client.messages.create(
                    max_tokens=settings.ANTHROPIC_MAX_TOKENS,
                    system=system,
                    messages=messages,
                    model=self.model,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stream=True,
                    timeout=settings.ANTHROPIC_TIMEOUT,
                )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        prompt_tokens = 0
        completion_tokens = 0
        with self.start_span(SpanType.CHUNK, SpanKind.SERVER):
            # pylint: disable=E1133
            for chunk in response:
                match chunk.type:
                    case ClaudeMessageType.MESSAGE_START:
                        chunk: RawMessageStartEvent
                        prompt_tokens = chunk.message.usage.input_tokens
                        self.log.chat_id = chunk.message.id
                    case ClaudeMessageType.MESSAGE_DELTA:
                        chunk: RawMessageDeltaEvent
                        completion_tokens = chunk.usage.output_tokens
                    case ClaudeMessageType.CONTENT_BLOCK_DELTA:
                        chunk: RawContentBlockDeltaEvent
                        yield chunk.delta.text
        await self.record(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

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
