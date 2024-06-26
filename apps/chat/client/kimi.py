from typing import List

from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from openai import OpenAI
from openai.types.chat import ChatCompletionChunk
from ovinc_client.core.logger import logger

from apps.chat.client.base import BaseClient
from apps.chat.exceptions import GenerateFailed
from apps.chat.models import Message


class KimiClient(BaseClient):
    """
    Kimi Client
    """

    def __init__(self, user: str, model: str, messages: List[Message], temperature: float, top_p: float):
        super().__init__(user=user, model=model, messages=messages, temperature=temperature, top_p=top_p)
        self.client = OpenAI(
            api_key=settings.KIMI_API_KEY,
            base_url=settings.KIMI_API_BASE_URL,
        )

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
        # pylint: disable=E1133
        prompt_tokens = 0
        completion_tokens = 0
        for chunk in response:
            self.record(response=chunk)
            usage = chunk.choices[0].model_extra.get("usage") or {}
            if usage:
                prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                completion_tokens = usage.get("completion_tokens", completion_tokens)
            yield chunk.choices[0].delta.content or ""
        self.finished_at = int(timezone.now().timestamp() * 1000)
        await self.post_chat(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

    # pylint: disable=W0221,R1710
    def record(self, response: ChatCompletionChunk, **kwargs) -> None:
        self.log.chat_id = response.id

    async def post_chat(self, prompt_tokens: int, completion_tokens: int) -> None:
        if not self.log:
            return
        # load usage
        self.log.prompt_tokens = prompt_tokens
        self.log.completion_tokens = completion_tokens
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.currency_unit = self.model_inst.currency_unit
        # save
        self.log.finished_at = self.finished_at
        await database_sync_to_async(self.log.save)()
