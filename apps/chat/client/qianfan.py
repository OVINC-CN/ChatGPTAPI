# pylint: disable=R0801

import qianfan
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from ovinc_client.core.logger import logger
from qianfan import QfResponse

from apps.chat.client.base import BaseClient
from apps.chat.exceptions import GenerateFailed

USER_MODEL = get_user_model()


class QianfanClient(BaseClient):
    """
    Baidu Qianfan
    """

    async def chat(self, *args, **kwargs) -> any:
        client = qianfan.ChatCompletion(ak=settings.QIANFAN_ACCESS_KEY, sk=settings.QIANFAN_SECRET_KEY)
        try:
            response = client.do(
                model=self.model,
                messages=self.messages,
                temperature=self.temperature,
                top_p=self.top_p,
                stream=True,
            )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        for chunk in response:
            self.record(response=chunk)
            yield chunk.body.get("result", "")
        self.finished_at = int(timezone.now().timestamp() * 1000)
        await self.post_chat()

    # pylint: disable=W0221,R1710
    def record(self, response: QfResponse, **kwargs) -> None:
        self.log.chat_id = response.body.get("id", "")
        self.log.content += response.body.get("result", "")
        usage = response.body.get("usage", {})
        self.log.prompt_tokens = usage.get("prompt_tokens", 0)
        self.log.completion_tokens = usage.get("completion_tokens", 0)

    async def post_chat(self) -> None:
        if not self.log:
            return
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.currency_unit = self.model_inst.currency_unit
        # save
        self.log.finished_at = self.finished_at
        await database_sync_to_async(self.log.save)()
        await database_sync_to_async(self.log.remove_content)()
