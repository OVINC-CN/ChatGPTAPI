# pylint: disable=R0801

from typing import List

from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext
from openai import OpenAI
from openai.types.chat import ChatCompletionChunk
from ovinc_client.core.logger import logger

from apps.chat.client.base import BaseClient, OpenAIToolMixin
from apps.chat.exceptions import GenerateFailed
from apps.chat.models import Message, ToolParams
from apps.chat.tools import TOOLS


class KimiClient(BaseClient, OpenAIToolMixin):
    """
    Kimi Client
    """

    # pylint: disable=R0913,R0917
    def __init__(
        self, user: str, model: str, messages: List[Message], temperature: float, top_p: float, tools: List[dict]
    ):
        super().__init__(user=user, model=model, messages=messages, temperature=temperature, top_p=top_p, tools=tools)
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
                tools=self.tools,
                tool_choice="auto" if self.tools else None,
            )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        prompt_tokens = 0
        completion_tokens = 0
        tool_params = ToolParams()
        # pylint: disable=E1133
        for chunk in response:
            self.record(response=chunk)
            usage = chunk.choices[0].model_extra.get("usage") or {}
            if usage:
                prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                completion_tokens = usage.get("completion_tokens", completion_tokens)
            yield chunk.choices[0].delta.content or ""
            # check tool use
            if chunk.choices[0].delta.tool_calls:
                tool_params.arguments += chunk.choices[0].delta.tool_calls[0].function.arguments
                tool_params.name = chunk.choices[0].delta.tool_calls[0].function.name or tool_params.name
                tool_params.type = chunk.choices[0].delta.tool_calls[0].type or tool_params.type
                tool_params.id = chunk.choices[0].delta.tool_calls[0].id or tool_params.id
        # call tool
        if tool_params.name:
            _message = gettext("[The result is using tool %s]") % str(TOOLS[tool_params.name].name_alias)
            yield _message
            yield "   \n   \n"
            async for i in self.use_tool(tool_params, *args, **kwargs):
                yield i
            prompt_tokens *= 2
            completion_tokens *= 2
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
