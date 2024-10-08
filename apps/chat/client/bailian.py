# pylint: disable=R0801

from http import HTTPStatus
from typing import Dict, Generator, List

from channels.db import database_sync_to_async
from dashscope import Application
from dashscope.app.application_response import ApplicationResponse
from django.utils import timezone
from ovinc_client.core.logger import logger

from apps.chat.client.base import BaseClient
from apps.chat.constants import BaiLianRole, OpenAIRole
from apps.chat.exceptions import GenerateFailed, UnexpectedError


class BaiLianClient(BaseClient):
    """
    Aliyun Bai Lian
    """

    async def chat(self, *args, **kwargs) -> any:
        try:
            response: Generator[ApplicationResponse, None, None] = Application.call(
                app_id=self.model,
                prompt=self.get_prompt(),
                history=self.get_history(),
                tempature=self.temperature,
                top_p=self.top_p,
                stream=True,
                incremental_output=True,
            )
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
            response = []
        for chunk in response:
            if chunk.status_code != HTTPStatus.OK:
                raise UnexpectedError(detail=chunk.message)
            self.record(chunk)
            yield chunk.output.text
        if not self.log:
            return
        self.log.finished_at = int(timezone.now().timestamp() * 1000)
        await database_sync_to_async(self.log.save)()

    # pylint: disable=W0221,R1710
    def record(self, response: ApplicationResponse) -> None:
        self.log.chat_id = response.request_id
        self.log.prompt_tokens = response.usage.models[0].input_tokens
        self.log.completion_tokens = response.usage.models[0].output_tokens
        self.log.prompt_token_unit_price = self.model_inst.prompt_price
        self.log.completion_token_unit_price = self.model_inst.completion_price

    def get_prompt(self) -> str:
        return self.messages[-1]["content"]

    def get_history(self) -> List[Dict[str, str]]:
        if len(self.messages) % 2 == 0:
            return []
        history = []
        temp_history = {}
        for message in self.messages[:-1]:
            key = ""
            match message["role"]:
                case OpenAIRole.ASSISTANT:
                    key = BaiLianRole.BOT
                case OpenAIRole.USER:
                    key = BaiLianRole.USER
                case OpenAIRole.SYSTEM:
                    key = BaiLianRole.USER
                case _:
                    continue
            temp_history[key] = message["content"]
            if len(temp_history.keys()) == 2:
                history.append(temp_history)
                temp_history = {}
        return history
