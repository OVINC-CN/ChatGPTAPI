import abc
import base64
import datetime

from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext
from httpx import AsyncClient, Client
from openai import OpenAI
from openai.types import CompletionUsage
from opentelemetry import trace
from opentelemetry.sdk.trace import Span
from opentelemetry.trace import SpanKind
from ovinc_client.core.logger import logger

from apps.chat.constants import MessageContentType, OpenAIRole, SpanType
from apps.chat.exceptions import FileExtractFailed
from apps.chat.models import AIModel, ChatLog, Message, MessageContent
from apps.chat.utils import format_error
from apps.cos.client import COSClient

USER_MODEL = get_user_model()


# pylint: disable=R0902
class BaseClient:
    """
    Base Client for Chat
    """

    # pylint: disable=R0913,R0917
    def __init__(self, user: str, model: str, messages: list[Message]):
        self.user: USER_MODEL = get_object_or_404(USER_MODEL, username=user)
        self.model: str = model
        self.model_inst: AIModel = AIModel.objects.get(model=model, is_enabled=True)
        self.model_settings: dict = self.model_inst.settings or {}
        self.messages = [
            message
            for message in messages
            if (message.role != OpenAIRole.SYSTEM or self.model_inst.support_system_define)
        ]
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

        with self.start_span(SpanType.AUDIT, SpanKind.INTERNAL):
            try:
                # prepare data
                audit_content = ""
                audit_image = []
                content = self.messages[-1].content
                if isinstance(content, list):
                    for item in content:
                        if item.type == MessageContentType.TEXT:
                            audit_content += str(item.text)
                        elif item.type == MessageContentType.IMAGE_URL:
                            audit_image.append(item.image_url.url)
                else:
                    audit_content = str(content)
                # call audit api
                client = COSClient()
                await client.text_audit(user=self.user, content=audit_content, data_id=self.log.id)
                for image in audit_image:
                    await client.image_audit(user=self.user, image_url=image, data_id=self.log.id)
            except Exception as e:
                await self.record()
                raise e

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

    @property
    def extra_headers(self) -> dict[str, str]:
        return {}

    @property
    def extra_body(self) -> dict | None:
        return None

    @property
    def extra_chat_params(self) -> dict[str, any]:
        return {}

    async def _chat(self, *args, **kwargs) -> any:
        image_count = await self.format_message()
        client = OpenAI(api_key=self.api_key, base_url=self.base_url, http_client=self.http_client)
        try:
            with self.start_span(SpanType.API, SpanKind.CLIENT):
                response = client.chat.completions.create(
                    model=self.api_model,
                    messages=[message.model_dump(exclude_none=True) for message in self.messages],
                    stream=True,
                    timeout=self.timeout,
                    stream_options={"include_usage": True},
                    extra_headers={
                        "HTTP-Referer": settings.PROJECT_URL,
                        "X-Title": settings.PROJECT_NAME,
                        **self.extra_headers,
                    },
                    extra_body=self.extra_body,
                    **self.extra_chat_params,
                )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield format_error(err)
            response = []
        prompt_tokens = 0
        completion_tokens = 0
        with self.start_span(SpanType.CHUNK, SpanKind.SERVER):
            for chunk in response:
                if chunk.choices:
                    yield chunk.choices[0].delta.content or ""
                if chunk.usage:
                    prompt_tokens, completion_tokens = self.get_tokens(chunk.usage)
                if chunk.id:
                    self.log.chat_id = chunk.id
        await self.record(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, vision_count=image_count)

    async def format_message(self) -> int:
        image_count = 0
        for message in self.messages:
            message: Message
            if not isinstance(message.content, list):
                continue
            for content in message.content:
                content: MessageContent
                if content.type != MessageContentType.IMAGE_URL or not content.image_url:
                    continue
                content.image_url.url = await self.convert_url_to_base64(content.image_url.url)
                image_count += 1
        return image_count

    async def convert_url_to_base64(self, url: str) -> str:
        client = AsyncClient(http2=True, timeout=settings.LOAD_IMAGE_TIMEOUT)
        try:
            response = await client.get(url)
            if response.status_code == 200:
                return f"data:image/webp;base64,{base64.b64encode(response.content).decode()}"
            raise FileExtractFailed(gettext("Parse Image To Base64 Failed"))
        finally:
            await client.aclose()

    def get_tokens(self, usage: CompletionUsage) -> (int, int):
        return (
            getattr(usage, "prompt_tokens", 0) or getattr(usage, "promptTokens", 0) or 0,
            getattr(usage, "completion_tokens", 0) or getattr(usage, "completionTokens", 0) or 0,
        )
