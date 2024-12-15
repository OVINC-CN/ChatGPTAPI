# pylint: disable=R0801

from typing import List

from django.conf import settings
from openai import OpenAI
from ovinc_client.core.logger import logger

from apps.chat.client.base import BaseClient
from apps.chat.exceptions import GenerateFailed


class KimiClient(BaseClient):
    """
    Kimi Client
    """

    # pylint: disable=R0913,R0917
    def __init__(self, user: str, model: str, messages: List[dict], temperature: float, top_p: float):
        super().__init__(user=user, model=model, messages=messages, temperature=temperature, top_p=top_p)
        self.client = OpenAI(
            api_key=settings.KIMI_API_KEY,
            base_url=settings.KIMI_API_BASE_URL,
        )

    async def _chat(self, *args, **kwargs) -> any:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
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
        # pylint: disable=E1133
        for chunk in response:
            self.log.chat_id = chunk.id
            usage = chunk.choices[0].model_extra.get("usage") or {}
            if usage:
                prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                completion_tokens = usage.get("completion_tokens", completion_tokens)
            yield chunk.choices[0].delta.content or ""
        await self.record(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
