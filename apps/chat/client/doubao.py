# pylint: disable=R0801

from typing import List

from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from openai.types.chat import ChatCompletionChunk
from ovinc_client.core.logger import logger
from volcenginesdkarkruntime import Ark

from apps.chat.client.base import BaseClient
from apps.chat.exceptions import GenerateFailed
from apps.chat.models import Message


class DoubaoClient(BaseClient):
    """
    Doubao Client
    """

    # pylint: disable=R0913,R0917
    def __init__(
        self, user: str, model: str, messages: List[Message], temperature: float, top_p: float, tools: List[dict]
    ):
        super().__init__(user=user, model=model, messages=messages, temperature=temperature, top_p=top_p, tools=tools)
        self.client = Ark(
            api_key=settings.DOUBAO_API_KEY,
            base_url=settings.DOUBAO_API_BASE_URL,
        )

    async def chat(self, *args, **kwargs) -> any:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=self.temperature,
                top_p=self.top_p,
                stream=True,
                stream_options={"include_usage": True},
            )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        prompt_tokens = 0
        completion_tokens = 0
        # pylint: disable=E1133
        for chunk in response:
            self.record(response=chunk)
            if chunk.choices:
                yield chunk.choices[0].delta.content or ""
            if chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens = chunk.usage.completion_tokens
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
        # save
        self.log.finished_at = self.finished_at
        await database_sync_to_async(self.log.save)()
