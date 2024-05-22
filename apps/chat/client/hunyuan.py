import json

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from tencentcloud.common import credential
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

from apps.chat.client.base import BaseClient
from apps.chat.models import ChatLog, HunYuanChuck


class HunYuanClient(BaseClient):
    """
    Hun Yuan
    """

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        # log
        self.created_at = int(timezone.now().timestamp() * 1000)
        # call hunyuan api
        response = self.call_api()
        # explain completion
        for chunk in response:
            chunk = json.loads(chunk["data"])
            chunk = HunYuanChuck.create(chunk)
            self.record(response=chunk)
            yield chunk.Choices[0].Delta.Content
        if not self.log:
            return
        self.log.finished_at = int(timezone.now().timestamp() * 1000)
        self.log.save()
        self.log.remove_content()

    # pylint: disable=W0221,R1710
    def record(self, response: HunYuanChuck) -> None:
        # check log exist
        if self.log:
            self.log.content += response.Choices[0].Delta.Content
            self.log.prompt_tokens = response.Usage.PromptTokens
            self.log.completion_tokens = response.Usage.CompletionTokens
            self.log.prompt_token_unit_price = self.model_inst.prompt_price
            self.log.completion_token_unit_price = self.model_inst.completion_price
            self.log.currency_unit = self.model_inst.currency_unit
            return
        # create log
        self.log = ChatLog.objects.create(
            chat_id=response.Id,
            user=self.user,
            model=self.model,
            messages=self.messages,
            content="",
            created_at=self.created_at,
        )
        return self.record(response=response)

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
