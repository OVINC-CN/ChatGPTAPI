from http import HTTPStatus
from typing import Dict, Generator, List

from dashscope import Application
from dashscope.app.application_response import ApplicationResponse
from django.utils import timezone

from apps.chat.client.base import BaseClient
from apps.chat.constants import BaiLianRole, OpenAIRole
from apps.chat.exceptions import UnexpectedError
from apps.chat.models import ChatLog


class BaiLianClient(BaseClient):
    """
    Aliyun Bai Lian
    """

    def chat(self, *args, **kwargs) -> any:
        self.created_at = int(timezone.now().timestamp() * 1000)
        response: Generator[ApplicationResponse, None, None] = Application.call(
            app_id=self.model,
            prompt=self.get_prompt(),
            history=self.get_history(),
            tempature=self.temperature,
            top_p=self.top_p,
            stream=True,
        )
        last_text = ""
        for chunk in response:
            if chunk.status_code != HTTPStatus.OK:
                raise UnexpectedError(detail=chunk.message)
            self.record(chunk)
            output = chunk.output.text[len(last_text) :]
            last_text = chunk.output.text
            yield output
        if not self.log:
            return
        self.log.finished_at = int(timezone.now().timestamp() * 1000)
        self.log.save()
        self.log.remove_content()

    def record(self, response: ApplicationResponse) -> None:
        # check log exist
        if self.log:
            self.log.content += response.output.text
            self.log.prompt_tokens = response.usage.models[0].input_tokens
            self.log.completion_tokens = response.usage.models[0].output_tokens
            self.log.prompt_token_unit_price = self.model_inst.prompt_price
            self.log.completion_token_unit_price = self.model_inst.completion_price
            self.log.currency_unit = self.model_inst.currency_unit
            return
        # create log
        self.log = ChatLog.objects.create(
            chat_id=response.request_id,
            user=self.user,
            model=self.model,
            messages=self.messages,
            content="",
            created_at=self.created_at,
        )
        return self.record(response=response)

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
