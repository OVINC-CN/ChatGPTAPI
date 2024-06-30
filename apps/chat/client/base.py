import abc
import datetime
import json
from typing import List

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from apps.chat.constants import OpenAIRole
from apps.chat.models import AIModel, ChatLog, Message, ToolParams
from apps.chat.tools import TOOLS

USER_MODEL = get_user_model()


# pylint: disable=R0902
class BaseClient:
    """
    Base Client for Chat
    """

    # pylint: disable=R0913
    def __init__(
        self, user: str, model: str, messages: List[Message], temperature: float, top_p: float, tools: List[dict]
    ):
        self.user: USER_MODEL = get_object_or_404(USER_MODEL, username=user)
        self.model: str = model
        self.model_inst: AIModel = AIModel.objects.get(model=model, is_enabled=True)
        self.model_settings: dict = self.model_inst.settings or {}
        self.messages: List[Message] = messages if self.model_inst.support_system_define else messages[1:]
        self.temperature: float = temperature
        self.top_p: float = top_p
        self.tools: List[dict] = (tools or None) if settings.CHATGPT_TOOLS_ENABLED else None
        self.finished_at: int = int()
        self.log = ChatLog.objects.create(
            user=self.user,
            model=self.model,
            created_at=int(datetime.datetime.now().timestamp() * 1000),
        )

    @abc.abstractmethod
    async def chat(self, *args, **kwargs) -> any:
        """
        Chat
        """

        raise NotImplementedError()

    @abc.abstractmethod
    def record(self, *args, **kwargs) -> None:
        """
        Record Log
        """

        raise NotImplementedError()


class OpenAIToolMixin:
    """
    OpenAI Tool Mixin
    """

    async def use_tool(self, tool_params: ToolParams, *args, **kwargs) -> any:
        self.messages.append(
            {
                "role": OpenAIRole.ASSISTANT.value,
                "tool_calls": [
                    {
                        "id": tool_params.id,
                        "type": tool_params.type,
                        "function": {
                            "arguments": tool_params.arguments,
                            "name": tool_params.name,
                        },
                    }
                ],
                "content": "",
            }
        )
        result = await TOOLS[tool_params.name](**json.loads(tool_params.arguments)).run()

        self.messages.append({"role": OpenAIRole.TOOL, "content": result, "tool_call_id": tool_params.id})

        async for i in self.chat(*args, **kwargs):
            yield i
