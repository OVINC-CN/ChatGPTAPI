from urllib.parse import urlparse, urlunparse

import tiktoken
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from httpx import Client
from openai import AzureOpenAI
from openai.types import ImagesResponse
from openai.types.chat import ChatCompletionChunk

from apps.chat.client.base import BaseClient
from apps.chat.models import ChatLog


class OpenAIClient(BaseClient):
    """
    OpenAI Client
    """

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
        client = AzureOpenAI(
            api_key=settings.OPENAI_API_KEY,
            api_version="2023-05-15",
            azure_endpoint=settings.OPENAI_API_BASE,
            http_client=Client(proxy=settings.OPENAI_HTTP_PROXY_URL) if settings.OPENAI_HTTP_PROXY_URL else None,
        )
        response = client.chat.completions.create(
            model=self.model.replace(".", ""),
            messages=self.messages,
            temperature=self.temperature,
            top_p=self.top_p,
            stream=True,
        )
        # pylint: disable=E1133
        for chunk in response:
            self.record(response=chunk)
            yield chunk.choices[0].delta.content or ""
        self.finished_at = int(timezone.now().timestamp() * 1000)
        self.post_chat()

    # pylint: disable=W0221,R1710
    def record(self, response: ChatCompletionChunk, **kwargs) -> None:
        # check log exist
        if self.log:
            self.log.content += response.choices[0].delta.content or ""
            return
        # create log
        self.log = ChatLog.objects.create(
            chat_id=response.id,
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
        # calculate tokens
        encoding = tiktoken.encoding_for_model(self.model)
        self.log.prompt_tokens = len(encoding.encode("".join([message["content"] for message in self.log.messages])))
        self.log.completion_tokens = len(encoding.encode(self.log.content))
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.currency_unit = self.model_inst.currency_unit
        # save
        self.log.finished_at = self.finished_at
        self.log.save()
        self.log.remove_content()


class OpenAIVisionClient(BaseClient):
    """
    OpenAI Vision Client
    """

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
        client = AzureOpenAI(
            api_key=settings.OPENAI_API_KEY,
            api_version="2023-12-01-preview",
            azure_endpoint=settings.OPENAI_API_BASE,
        )
        response = client.images.generate(
            model=self.model.replace(".", ""),
            prompt=self.messages[-1]["content"],
            n=1,
            size=self.model_inst.vision_size,
            quality=self.model_inst.vision_quality,
            style=self.model_inst.vision_style,
        )
        self.record(response=response)
        raw_url = urlparse(url=response.data[0].url)
        cos_url = urlparse(url=settings.QCLOUD_COS_URL)
        new_url = urlunparse(
            (
                cos_url.scheme,
                cos_url.netloc,
                raw_url.path,
                raw_url.params,
                raw_url.query,
                raw_url.fragment,
            )
        )
        return f"![{self.messages[-1]['content']}]({new_url})"

    # pylint: disable=W0221,R1710
    def record(self, response: ImagesResponse, **kwargs) -> None:
        self.log = ChatLog.objects.create(
            user=self.user,
            model=self.model,
            messages=self.messages,
            content=response.data[0].url,
            completion_tokens=1,
            completion_token_unit_price=self.model_inst.completion_price,
            currency_unit=self.model_inst.currency_unit,
            created_at=self.created_at,
            finished_at=int(timezone.now().timestamp() * 1000),
        )
        self.log.remove_content()
