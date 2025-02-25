import abc
import base64
import datetime
import math

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext
from httpx import Client
from openai import OpenAI
from openai.types import CompletionUsage
from opentelemetry import trace
from opentelemetry.sdk.trace import Span
from opentelemetry.trace import SpanKind
from ovinc_client.core.logger import logger

from apps.chat.constants import MessageContentType, OpenAIRole, SpanType, ThinkStatus
from apps.chat.exceptions import FileExtractFailed
from apps.chat.models import AIModel, ChatLog, Message, MessageContent
from apps.chat.tasks import calculate_usage_limit
from apps.chat.utils import format_error, format_response
from apps.cos.client import COSClient
from utils.prometheus.constants import PrometheusLabels, PrometheusMetrics
from utils.prometheus.exporters import PrometheusExporter

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

    def chat(self, *args, **kwargs) -> any:
        """
        Chat
        """

        with self.start_span(SpanType.AUDIT, SpanKind.SERVER):
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
                client.text_audit(user=self.user, content=audit_content, data_id=self.log.id)
                for image in audit_image:
                    client.image_audit(user=self.user, image_url=image, data_id=self.log.id)
            except Exception as err:
                self.record()
                raise err

        with self.start_span(SpanType.CHAT, SpanKind.SERVER):
            try:
                yield from self._chat(*args, **kwargs)
            except Exception as err:
                self.record()
                raise err

    @abc.abstractmethod
    def _chat(self, *args, **kwargs) -> any:
        """
        Chat
        """

        raise NotImplementedError()

    def record(self, prompt_tokens: int = 0, completion_tokens: int = 0, vision_count: int = 0) -> None:
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
        self.log.save()
        # calculate usage
        calculate_usage_limit(log_id=self.log.id)  # pylint: disable=E1120

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
    def extra_query(self) -> dict | None:
        return None

    @property
    def extra_body(self) -> dict | None:
        return None

    @property
    def extra_chat_params(self) -> dict[str, any]:
        return {}

    @property
    def use_stream(self) -> bool:
        return True

    @property
    def thinking_key(self) -> str:
        return ""

    def _chat(self, *args, **kwargs) -> any:
        image_count = self.format_message()
        client = OpenAI(api_key=self.api_key, base_url=self.base_url, http_client=self.http_client)
        req_time = PrometheusExporter.current_ts()
        try:
            with self.start_span(SpanType.API, SpanKind.CLIENT):
                response = client.chat.completions.create(
                    model=self.api_model,
                    messages=[message.model_dump(exclude_none=True) for message in self.messages],
                    stream=self.use_stream,
                    timeout=self.timeout,
                    stream_options={"include_usage": True} if self.use_stream else None,
                    extra_headers={
                        "HTTP-Referer": settings.PROJECT_URL,
                        "X-Title": settings.PROJECT_NAME,
                        **self.extra_headers,
                    },
                    extra_query=self.extra_query,
                    extra_body=self.extra_body,
                    **self.extra_chat_params,
                )
        except Exception as err:  # pylint: disable=W0718
            logger.error("[GenerateContentFailed] %s", err)
            yield format_error(self.log.id, err)
            response = []
        if not self.use_stream:
            response = [response]
        yield from self.parse_response(response=response, image_count=image_count, req_time=req_time)

    def parse_response(self, response, image_count, req_time) -> None:
        prompt_tokens = 0
        completion_tokens = 0
        is_first_letter = True
        first_letter_time = PrometheusExporter.current_ts()
        think_status = ThinkStatus.NOT_START
        with self.start_span(SpanType.CHUNK, SpanKind.SERVER):
            for chunk in response:
                if chunk.choices:
                    content = chunk.choices[0].delta.content if self.use_stream else chunk.choices[0].message.content
                    if is_first_letter and content:
                        is_first_letter = False
                        first_letter_time = PrometheusExporter.current_ts()
                        self.report_metric(name=PrometheusMetrics.WAIT_FIRST_LETTER, value=first_letter_time - req_time)
                    if content:
                        data, reasoning_content, think_status = self.parse_think_tag(
                            chunk=content, think_status=think_status
                        )
                        if data or reasoning_content:
                            yield format_response(log_id=self.log.id, data=data, thinking=reasoning_content)
                    elif self.thinking_key:
                        # reasoning content
                        reasoning_content = (
                            getattr(chunk.choices[0].delta, self.thinking_key, "")
                            if self.use_stream
                            else getattr(chunk.choices[0].message, self.thinking_key, "")
                        )
                        if reasoning_content:
                            yield format_response(log_id=self.log.id, thinking=reasoning_content)
                if chunk.usage:
                    prompt_tokens, completion_tokens = self.get_tokens(chunk.usage)
                if chunk.id and not self.log.chat_id:
                    self.log.chat_id = chunk.id
        finish_chat_time = PrometheusExporter.current_ts()
        self.record(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, vision_count=image_count)
        self.report_metric(
            name=PrometheusMetrics.TOKEN_PER_SECOND,
            value=math.ceil(completion_tokens / max(finish_chat_time - first_letter_time, 1) * 1000),
        )
        self.report_metric(name=PrometheusMetrics.PROMPT_TOKEN, value=prompt_tokens)
        self.report_metric(name=PrometheusMetrics.COMPLETION_TOKEN, value=completion_tokens)

    def parse_think_tag(self, chunk: str, think_status: int) -> (str, str, int):
        match think_status:
            case ThinkStatus.NOT_START:
                if chunk == "<think>":
                    return "", "", ThinkStatus.THINKING
                return chunk, "", ThinkStatus.NOT_START
            case ThinkStatus.THINKING:
                if chunk == "</think>":
                    return "", "", ThinkStatus.COMPLETED
                return "", chunk, ThinkStatus.THINKING
            case ThinkStatus.COMPLETED:
                return chunk, "", ThinkStatus.COMPLETED

    def report_metric(self, name: str, value: float) -> None:
        PrometheusExporter(
            name=name,
            samples=[(None, value)],
            labels=[
                (PrometheusLabels.MODEL_NAME, self.model),
                (PrometheusLabels.HOSTNAME, PrometheusExporter.hostname()),
            ],
        ).export()

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
        client = Client(http2=True, timeout=settings.LOAD_IMAGE_TIMEOUT)
        try:
            response = client.get(url)
            if response.status_code == 200:
                return f"data:image/webp;base64,{base64.b64encode(response.content).decode()}"
            raise FileExtractFailed(gettext("Parse Image To Base64 Failed"))
        finally:
            client.close()

    def get_tokens(self, usage: CompletionUsage) -> (int, int):
        return (
            getattr(usage, "prompt_tokens", 0) or getattr(usage, "promptTokens", 0) or 0,
            getattr(usage, "completion_tokens", 0) or getattr(usage, "completionTokens", 0) or 0,
        )
