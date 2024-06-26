# pylint: disable=R0801

import json

from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from ovinc_client.core.logger import logger
from tencentcloud.common import credential
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

from apps.chat.client.base import BaseClient
from apps.chat.exceptions import GenerateFailed
from apps.chat.models import HunYuanChuck


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
        self.log.currency_unit = self.model_inst.currency_unit

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
        }
        req.from_json_string(json.dumps(params))
        return client.ChatCompletions(req)
