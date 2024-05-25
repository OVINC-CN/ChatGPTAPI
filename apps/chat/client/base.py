import abc
from typing import List

from django.contrib.auth import get_user_model
from rest_framework.request import Request

from apps.chat.models import AIModel, ChatLog, Message

USER_MODEL = get_user_model()


# pylint: disable=R0902
class BaseClient:
    """
    Base Client for Chat
    """

    # pylint: disable=R0913
    def __init__(self, request: Request, model: str, messages: List[Message], temperature: float, top_p: float):
        self.log: ChatLog = None
        self.request: Request = request
        self.user: USER_MODEL = request.user
        self.model: str = model
        self.model_inst: AIModel = AIModel.objects.get(model=model, is_enabled=True)
        self.model_settings: dict = self.model_inst.settings or {}
        self.messages: List[Message] = messages
        self.temperature: float = temperature
        self.top_p: float = top_p
        self.created_at: int = int()
        self.finished_at: int = int()

    @abc.abstractmethod
    def chat(self, *args, **kwargs) -> any:
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
