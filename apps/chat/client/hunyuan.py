# pylint: disable=R0801
import asyncio
import json
import time
import uuid

import httpx
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
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
)
from apps.chat.exceptions import GenerateFailed, LoadImageFailed
from apps.chat.models import HunYuanChuck
from apps.cos.client import COSClient


class HunYuanClient(BaseClient):
    """
    Hun Yuan
    """

    async def chat(self, *args, **kwargs) -> any:
        # call hunyuan api
        try:
            response = self.call_api()
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        # explain completion
        for chunk in response:
            chunk = json.loads(chunk["data"])
            chunk = HunYuanChuck.create(chunk)
            self.record(response=chunk)
            yield chunk.Choices[0].Delta.Content
        if not self.log:
            return
        self.log.finished_at = int(timezone.now().timestamp() * 1000)
        await database_sync_to_async(self.log.save)()

    # pylint: disable=W0221,R1710
    def record(self, response: HunYuanChuck) -> None:
        self.log.chat_id = response.Id
        self.log.prompt_tokens = response.Usage.PromptTokens
        self.log.completion_tokens = response.Usage.CompletionTokens
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price

    def call_api(self) -> models.ChatCompletionsResponse:
        client = hunyuan_client.HunyuanClient(
            credential.Credential(settings.QCLOUD_SECRET_ID, settings.QCLOUD_SECRET_KEY), ""
        )
        req = models.ChatCompletionsRequest()
        params = {
            "Model": self.model,
            "Messages": [{"Role": message["role"], "Content": message["content"]} for message in self.messages],
            "TopP": self.top_p,
            "Temperature": self.temperature,
            "Stream": True,
            "EnableEnhancement": False,
        }
        req.from_json_string(json.dumps(params))
        return client.ChatCompletions(req)


class HunYuanVisionClient(BaseClient):
    """
    Hunyuan Vision Client
    """

    async def chat(self, *args, **kwargs) -> any:
        # init client
        client = hunyuan_client.HunyuanClient(
            credential.Credential(settings.QCLOUD_SECRET_ID, settings.QCLOUD_SECRET_KEY),
            settings.HUNYUAN_IMAGE_API_REGION,
        )
        # call hunyuan api
        try:
            # submit job
            response = self.call_api(client)
            # wait for result
            start_time = time.time()
            while time.time() - start_time < settings.HUNYUAN_IMAGE_JOB_TIMEOUT:
                result = self.call_result_api(client, response.JobId)
                # if not finished, continue loop
                if result.JobStatusCode in [HunyuanJobStatusCode.RUNNING, HunyuanJobStatusCode.WAITING]:
                    yield ""
                    await asyncio.sleep(settings.HUNYUAN_IMAGE_JOB_INTERVAL)
                    continue
                # if finished, check result
                if result.JobStatusCode == HunyuanJobStatusCode.FINISHED:
                    # all failed
                    if all(i != HUNYUAN_SUCCESS_DETAIL for i in result.ResultDetails):
                        yield str(GenerateFailed())
                        break
                    # record
                    await self.record(response=response, result=result)
                    # use first success picture
                    message_index = min(
                        index for (index, detail) in enumerate(result.ResultDetails) if detail == HUNYUAN_SUCCESS_DETAIL
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
                    yield f"![output]({url}?{settings.QCLOUD_COS_IMAGE_STYLE})"
                else:
                    yield f"{result.JobErrorMsg}({result.JobErrorCode})"
                break
        except TencentCloudSDKException as err:
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(err.message)
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())

    # pylint: disable=W0221,R1710,W0236
    async def record(
        self, response: models.SubmitHunyuanImageJobResponse, result: models.QueryHunyuanImageJobResponse
    ) -> None:
        self.log.chat_id = response.JobId
        self.log.completion_tokens = len(result.ResultImage)
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.finished_at = int(timezone.now().timestamp() * 1000)
        await database_sync_to_async(self.log.save)()

    def call_api(self, client: hunyuan_client) -> models.SubmitHunyuanImageJobResponse:
        req = models.SubmitHunyuanImageJobRequest()
        params = {
            "Prompt": self.messages[-1]["content"],
            "LogoAdd": HunyuanLogoControl.REMOVE,
            "Revise": HunyuanReviseControl.ENABLED,
        }
        req.from_json_string(json.dumps(params))
        return client.SubmitHunyuanImageJob(req)

    def call_result_api(self, client: hunyuan_client, job_id: str) -> models.QueryHunyuanImageJobResponse:
        req = models.QueryHunyuanImageJobRequest()
        req.from_json_string(json.dumps({"JobId": job_id}))
        return client.QueryHunyuanImageJob(req)
