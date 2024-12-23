import abc
import base64
import datetime

from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext
from httpx import Client
from openai import OpenAI
from opentelemetry import trace
from opentelemetry.sdk.trace import Span
from opentelemetry.trace import SpanKind
from ovinc_client.core.logger import logger

from apps.chat.constants import MessageContentType, OpenAIRole, SpanType
from apps.chat.exceptions import FileExtractFailed, GenerateFailed
from apps.chat.models import AIModel, ChatLog, Message, MessageContent

USER_MODEL = get_user_model()


# pylint: disable=R0902
class BaseClient:
    """
    Base Client for Chat
    """

    # pylint: disable=R0913,R0917
    def __init__(self, user: str, model: str, messages: list[Message], temperature: float, top_p: float):
        self.user: USER_MODEL = get_object_or_404(USER_MODEL, username=user)
        self.model: str = model
        self.model_inst: AIModel = AIModel.objects.get(model=model, is_enabled=True)
        self.model_settings: dict = self.model_inst.settings or {}
        self.messages = [
            message
            for message in messages
            if (message.role != OpenAIRole.SYSTEM or self.model_inst.support_system_define)
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

    async def record(self, prompt_tokens: int = 0, completion_tokens: int = 0, vision_count: int = 0) -> None:
        if not self.log:
            return
        # calculate tokens
        self.log.prompt_tokens = max(prompt_tokens, self.log.prompt_tokens)
        self.log.completion_tokens = max(completion_tokens, self.log.completion_tokens)
        self.log.vision_count = max(vision_count, self.log.vision_count)
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.vision_unit_price = self.model_inst.vision_price
        self.log.request_unit_price = self.model_inst.request_price
        # save
        self.log.finished_at = int(timezone.now().timestamp() * 1000)
        await database_sync_to_async(self.log.save)()
        # calculate usage
        from apps.chat.tasks import calculate_usage_limit  # pylint: disable=C0415

        await database_sync_to_async(calculate_usage_limit)(log_id=self.log.id)  # pylint: disable=E1120

    def start_span(self, name: str, kind: SpanKind, **kwargs) -> Span:
        span: Span = self.tracer.start_as_current_span(name=name, kind=kind, **kwargs)
        return span


class OpenAIBaseClient(BaseClient, abc.ABC):
    """
    OpenAI Client
    """

    @property
    @abc.abstractmethod
    def api_key(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def base_url(self) -> str:
        raise NotImplementedError()

    @property
    def http_client(self) -> Client | None:
        return None

    @property
    def timeout(self) -> int:
        return settings.OPENAI_CHAT_TIMEOUT

    @property
    def api_model(self) -> str:
        return self.model

    async def _chat(self, *args, **kwargs) -> any:
        image_count = self.format_message()
        client = OpenAI(api_key=self.api_key, base_url=self.base_url, http_client=self.http_client)
        try:
            with self.start_span(SpanType.API, SpanKind.CLIENT):
                response = client.chat.completions.create(
                    model=self.api_model,
                    messages=[message.model_dump(exclude_none=True) for message in self.messages],
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stream=True,
                    timeout=self.timeout,
                    stream_options={"include_usage": True},
                    extra_headers={"HTTP-Referer": settings.PROJECT_URL, "X-Title": settings.PROJECT_NAME},
                )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        prompt_tokens = 0
        completion_tokens = 0
        with self.start_span(SpanType.CHUNK, SpanKind.SERVER):
            for chunk in response:
                if chunk.choices:
                    yield chunk.choices[0].delta.content or ""
                if chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens
                if chunk.id:
                    self.log.chat_id = chunk.id
        await self.record(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, vision_count=image_count)

    def format_message(self) -> int:
        image_count = 0
        for message in self.messages:
            message: Message
            if not isinstance(message.content, list):
                continue
            for content in message.content:
                content: MessageContent
                if content.type != MessageContentType.IMAGE_URL or not content.image_url:
                    continue
                content.image_url.url = self.convert_url_to_base64(content.image_url.url)
                image_count += 1
        return image_count

    def convert_url_to_base64(self, url: str) -> str:
        with Client(http2=True) as client:
            response = client.get(url)
            if response.status_code == 200:
                return f"data:image/webp;base64,{base64.b64encode(response.content).decode()}"
            raise FileExtractFailed(gettext("Parse Image To Base64 Failed"))
