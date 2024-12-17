# pylint: disable=R0801


from django.conf import settings
from openai import OpenAI
from opentelemetry.trace import SpanKind
from ovinc_client.core.logger import logger

from apps.chat.client.base import BaseClient
from apps.chat.constants import SpanType
from apps.chat.exceptions import GenerateFailed


class KimiClient(BaseClient):
    """
    Kimi Client
    """

    async def _chat(self, *args, **kwargs) -> any:
        client = OpenAI(api_key=settings.KIMI_API_KEY, base_url=settings.KIMI_API_BASE_URL)
        try:
            with self.start_span(SpanType.API, SpanKind.CLIENT):
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[message.model_dump(exclude_none=True) for message in self.messages],
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stream=True,
                    timeout=settings.KIMI_CHAT_TIMEOUT,
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
                self.log.chat_id = chunk.id
                usage = chunk.choices[0].model_extra.get("usage") or {}
                if usage:
                    prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                    completion_tokens = usage.get("completion_tokens", completion_tokens)
                yield chunk.choices[0].delta.content or ""
        await self.record(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
