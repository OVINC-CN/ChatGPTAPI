from typing import List

import google.generativeai as genai
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from google.generativeai.types import GenerateContentResponse
from rest_framework.request import Request

from apps.chat.client.base import BaseClient
from apps.chat.constants import GeminiRole, OpenAIRole
from apps.chat.models import ChatLog, Message


class GeminiClient(BaseClient):
    """
    Gemini Pro
    """

    # pylint: disable=R0913
    def __init__(self, request: Request, model: str, messages: List[Message], temperature: float, top_p: float):
        super().__init__(request=request, model=model, messages=messages, temperature=temperature, top_p=top_p)
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.genai_model = genai.GenerativeModel("gemini-pro")

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
        response = self.genai_model.generate_content(
            contents=[
                {"role": self.get_role(message["role"]), "parts": [message["content"]]} for message in self.messages
            ],
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
                top_p=self.top_p,
            ),
            stream=True,
        )
        for chunk in response:
            self.record(response=chunk)
            yield chunk.text
        self.finished_at = int(timezone.now().timestamp() * 1000)
        self.post_chat()

    @classmethod
    def get_role(cls, role: str) -> str:
        if role == OpenAIRole.ASSISTANT:
            return GeminiRole.MODEL
        return GeminiRole.USER

    # pylint: disable=W0221,R1710
    def record(self, response: GenerateContentResponse, **kwargs) -> None:
        # check log exist
        if self.log:
            self.log.content += response.text
            return
        # create log
        self.log = ChatLog.objects.create(
            user=self.user,
            model=self.model,
            messages=self.messages,
            content="",
            created_at=self.created_at,
        )
        return self.record(response=response)

    def post_chat(self) -> None:
        if not self.log:
            return
        # calculate characters
        self.log.prompt_tokens = len("".join([message["content"] for message in self.log.messages]))
        self.log.completion_tokens = len(self.log.content)
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.currency_unit = self.model_inst.currency_unit
        # save
        self.log.finished_at = self.finished_at
        self.log.save()
        self.log.remove_content()
