# pylint: disable=R0801

import asyncio
import json
import time
import uuid

import httpx
from django.conf import settings
from opentelemetry.trace import SpanKind
from ovinc_client.core.logger import logger
from rest_framework import status
from tencentcloud.common import credential
from tencentcloud.common.exception import TencentCloudSDKException
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

from apps.chat.client.base import BaseClient
from apps.chat.constants import (
    HUNYUAN_SUCCESS_DETAIL,
    HunyuanJobStatusCode,
    HunyuanLogoControl,
    HunyuanReviseControl,
    MessageContentType,
    SpanType,
)
from apps.chat.exceptions import GenerateFailed, LoadImageFailed
from apps.chat.models import HunYuanChuck, MessageContent
from apps.cos.client import COSClient
from apps.cos.utils import TCloudUrlParser


class HunYuanClient(BaseClient):
    """
    Hun Yuan
    """

    async def _chat(self, *args, **kwargs) -> any:
        # call hunyuan api
        try:
            with self.start_span(SpanType.API, SpanKind.CLIENT):
                response = self.call_api()
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        # init
        prompt_tokens = 0
        completion_tokens = 0
        # explain completion
        with self.start_span(SpanType.CHUNK, SpanKind.SERVER):
            for chunk in response:
                chunk = HunYuanChuck(**json.loads(chunk["data"]))
                self.log.chat_id = chunk.Id
                prompt_tokens = chunk.Usage.PromptTokens
                completion_tokens = chunk.Usage.CompletionTokens
                if chunk.Choices:
                    yield chunk.Choices[0].Delta.Content
        await self.record(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

    def call_api(self) -> models.ChatCompletionsResponse:
        client = hunyuan_client.HunyuanClient(
            credential.Credential(settings.QCLOUD_SECRET_ID, settings.QCLOUD_SECRET_KEY), ""
        )
        req = models.ChatCompletionsRequest()
        params = {
            "Model": self.model,
            "Messages": [{"Role": message.role, **self.parse_content(message.content)} for message in self.messages],
            "TopP": self.top_p,
            "Temperature": self.temperature,
            "Stream": True,
            "EnableEnhancement": False,
        }
        req.from_json_string(json.dumps(params))
        return client.ChatCompletions(req)

    def parse_content(self, content: str | list[MessageContent]) -> dict:
        if isinstance(content, list):
            new_content = []
            for content_item in content:
                if content_item.type == MessageContentType.TEXT:
                    new_content.append(
                        {
                            "Type": MessageContentType.TEXT,
                            "Text": content_item.text,
                        }
                    )
                elif content_item.type == MessageContentType.IMAGE_URL:
                    new_content.append(
                        {
                            "Type": MessageContentType.IMAGE_URL,
                            "ImageUrl": {
                                "Url": content_item.image_url.url,
                            },
                        }
                    )
            return {"Contents": new_content}
        return {"Content": content}


class HunYuanVisionClient(BaseClient):
    """
    Hunyuan Vision Client
    """

    async def _chat(self, *args, **kwargs) -> any:
        # init client
        client = hunyuan_client.HunyuanClient(
            credential.Credential(settings.QCLOUD_SECRET_ID, settings.QCLOUD_SECRET_KEY),
            settings.HUNYUAN_IMAGE_API_REGION,
        )
        # call hunyuan api
        try:
            # submit job
            with self.start_span(SpanType.API, SpanKind.CLIENT):
                response = self.call_api(client)
            # wait for result
            start_time = time.time()
            while time.time() - start_time < settings.HUNYUAN_IMAGE_JOB_TIMEOUT:
                with self.start_span(SpanType.FETCH, SpanKind.CLIENT):
                    result = self.call_result_api(client, response.JobId)
                # if not finished, continue loop
                if result.JobStatusCode in [HunyuanJobStatusCode.RUNNING, HunyuanJobStatusCode.WAITING]:
                    yield ""
                    await asyncio.sleep(settings.HUNYUAN_IMAGE_JOB_INTERVAL)
                    continue
                # if finished, check result
                if result.JobStatusCode == HunyuanJobStatusCode.FINISHED:
                    await self.record(completion_tokens=len(result.ResultImage))
                    # all failed
                    if all(i != HUNYUAN_SUCCESS_DETAIL for i in result.ResultDetails):
                        yield str(GenerateFailed())
                        break
                    with self.start_span(SpanType.CHUNK, SpanKind.SERVER):
                        # record
                        self.log.chat_id = response.JobId
                        # use first success picture
                        message_index = min(
                            index
                            for (index, detail) in enumerate(result.ResultDetails)
                            if detail == HUNYUAN_SUCCESS_DETAIL
                        )
                        message_url = result.ResultImage[message_index]
                        httpx_client = httpx.AsyncClient(http2=True)
                        image_resp = await httpx_client.get(message_url)
                        await httpx_client.aclose()
                        if image_resp.status_code != status.HTTP_200_OK:
                            raise LoadImageFailed()
                        url = await COSClient().put_object(
                            file=image_resp.content,
                            file_name=f"{uuid.uuid4().hex}.{image_resp.headers['content-type'].split('/')[-1]}",
                        )
                        yield f"![output]({TCloudUrlParser(url).url})"
                else:
                    yield f"{result.JobErrorMsg}({result.JobErrorCode})"
                    await self.record()
                break
        except TencentCloudSDKException as err:
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(err.message)
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())

    def call_api(self, client: hunyuan_client) -> models.SubmitHunyuanImageJobResponse:
        req = models.SubmitHunyuanImageJobRequest()
        params = {
            "Prompt": self.messages[-1].content,
            "LogoAdd": HunyuanLogoControl.REMOVE,
            "Revise": HunyuanReviseControl.ENABLED,
        }
        req.from_json_string(json.dumps(params))
        return client.SubmitHunyuanImageJob(req)

    def call_result_api(self, client: hunyuan_client, job_id: str) -> models.QueryHunyuanImageJobResponse:
        req = models.QueryHunyuanImageJobRequest()
        req.from_json_string(json.dumps({"JobId": job_id}))
        return client.QueryHunyuanImageJob(req)
