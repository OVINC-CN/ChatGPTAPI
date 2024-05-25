# pylint: disable=R0801

import qianfan
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from ovinc_client.core.logger import logger
from qianfan import QfResponse

from apps.chat.client.base import BaseClient
from apps.chat.exceptions import GenerateFailed
from apps.chat.models import ChatLog

USER_MODEL = get_user_model()


class QianfanClient(BaseClient):
    """
    Baidu Qianfan
    """

    @transaction.atomic()
    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
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
        self.post_chat()

    # pylint: disable=W0221,R1710
    def record(self, response: QfResponse, **kwargs) -> None:
        # check log exist
        if self.log:
            self.log.content += response.body.get("result", "")
            usage = response.body.get("usage", {})
            self.log.prompt_tokens = usage.get("prompt_tokens", 0)
            self.log.completion_tokens = usage.get("completion_tokens", 0)
            return
        # create log
        self.log = ChatLog.objects.create(
            chat_id=response.body.get("id", ""),
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
        # calculate price
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.currency_unit = self.model_inst.currency_unit
        # save
        self.log.finished_at = self.finished_at
        self.log.save()
        self.log.remove_content()
