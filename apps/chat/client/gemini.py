# pylint: disable=R0801

from typing import List

import google.generativeai as genai
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from google.generativeai.types import GenerateContentResponse
from ovinc_client.core.logger import logger

from apps.chat.client.base import BaseClient
from apps.chat.constants import GeminiRole, OpenAIRole
from apps.chat.exceptions import GenerateFailed
from apps.chat.models import Message


class GeminiClient(BaseClient):
    """
    Gemini Pro
    """

    # pylint: disable=R0913,R0917
    def __init__(self, user: str, model: str, messages: List[Message], temperature: float, top_p: float):
        super().__init__(user=user, model=model, messages=messages, temperature=temperature, top_p=top_p)
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.genai_model = genai.GenerativeModel(self.model)

    async def chat(self, *args, **kwargs) -> any:
        contents = [
            {"role": self.get_role(message["role"]), "parts": [message["content"]]} for message in self.messages
        ]
        try:
            response = self.genai_model.generate_content(
                contents=contents,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    top_p=self.top_p,
                ),
                stream=True,
            )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        for chunk in response:
            self.record(response=chunk)
            yield chunk.text
        self.finished_at = int(timezone.now().timestamp() * 1000)
        await self.post_chat(contents=contents, response=response)

    @classmethod
    def get_role(cls, role: str) -> str:
        if role == OpenAIRole.ASSISTANT:
            return GeminiRole.MODEL
        return GeminiRole.USER

    # pylint: disable=W0221,R1710
    def record(self, response: GenerateContentResponse, **kwargs) -> None:
        pass

    async def post_chat(self, contents: List[Message], response: any) -> None:
        if not self.log:
            return
        # calculate characters
        self.log.prompt_tokens = self.genai_model.count_tokens(contents).total_tokens
        self.log.completion_tokens = self.genai_model.count_tokens(response.text).total_tokens
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        # save
        self.log.finished_at = self.finished_at
        await database_sync_to_async(self.log.save)()
