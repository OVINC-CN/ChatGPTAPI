import abc
import datetime
from typing import List

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from opentelemetry import trace
from opentelemetry.sdk.trace import Span
from opentelemetry.trace import SpanKind

from apps.chat.constants import OpenAIRole, SpanType
from apps.chat.models import AIModel, ChatLog

USER_MODEL = get_user_model()


# pylint: disable=R0902
class BaseClient:
    """
    Base Client for Chat
    """

    # pylint: disable=R0913,R0917
    def __init__(self, user: str, model: str, messages: List[dict], temperature: float, top_p: float):
        self.user: USER_MODEL = get_object_or_404(USER_MODEL, username=user)
        self.model: str = model
        self.model_inst: AIModel = AIModel.objects.get(model=model, is_enabled=True)
        self.model_settings: dict = self.model_inst.settings or {}
        self.messages: List[dict] = [
            message
            for message in messages
            if (message["role"] != OpenAIRole.SYSTEM or self.model_inst.support_system_define)
        ]
        self.temperature: float = temperature
        self.top_p: float = top_p
        self.log = ChatLog.objects.create(
            user=self.user,
            model=self.model,
            created_at=int(datetime.datetime.now().timestamp() * 1000),
        )
        self.tracer = trace.get_tracer(self.__class__.__name__)

    async def chat(self, *args, **kwargs) -> any:
        """
        Chat
        """

        with self.start_span(SpanType.CHAT, SpanKind.SERVER):
            try:
                async for text in self._chat(*args, **kwargs):
                    yield text
            except Exception as e:
                await self.record()
                raise e

    @abc.abstractmethod
    async def _chat(self, *args, **kwargs) -> any:
        """
        Chat
        """

        raise NotImplementedError()

    async def record(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        if not self.log:
            return
        # calculate tokens
        self.log.prompt_tokens = max(prompt_tokens, self.log.prompt_tokens)
        self.log.completion_tokens = max(completion_tokens, self.log.completion_tokens)
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        # save
        self.log.finished_at = int(timezone.now().timestamp() * 1000)
        await database_sync_to_async(self.log.save)()

    def start_span(self, name: str, kind: SpanKind, **kwargs) -> Span:
        span: Span = self.tracer.start_as_current_span(name=name, kind=kind, **kwargs)
        return span
