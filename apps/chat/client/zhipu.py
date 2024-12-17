# pylint: disable=R0801

from typing import List

from django.conf import settings
from openai import OpenAI
from opentelemetry.trace import SpanKind
from ovinc_client.core.logger import logger

from apps.chat.client.base import BaseClient
from apps.chat.constants import SpanType
from apps.chat.exceptions import GenerateFailed


class ZhipuClient(BaseClient):
    """
    Zhipu Client
    """

    # pylint: disable=R0913,R0917
    def __init__(self, user: str, model: str, messages: List[dict], temperature: float, top_p: float):
        super().__init__(user=user, model=model, messages=messages, temperature=temperature, top_p=top_p)
        self.client = OpenAI(api_key=settings.ZHIPU_API_KEY, base_url=settings.ZHIPU_API_URL)

    async def _chat(self, *args, **kwargs) -> any:
        try:
            with self.start_span(SpanType.API, SpanKind.CLIENT):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stream=True,
                    timeout=settings.ZHIPU_API_TIMEOUT,
                    stream_options={"include_usage": True},
                )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        content = ""
        prompt_tokens = 0
        completion_tokens = 0
        with self.start_span(SpanType.CHUNK, SpanKind.SERVER):
            # pylint: disable=E1133
            for chunk in response:
                self.log.chat_id = chunk.id
                if chunk.choices:
                    content += chunk.choices[0].delta.content or ""
                    yield chunk.choices[0].delta.content or ""
                if chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens
        await self.record(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
