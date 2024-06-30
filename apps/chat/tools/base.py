import abc

from django.utils.translation import gettext

from apps.chat.constants import ToolType


class Tool:
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        English Name
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def name_alias(self) -> str:
        """
        Localization Name
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def desc(self) -> str:
        """
        English Description
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def desc_alias(self) -> str:
        """
        Localization Description
        """
        raise NotImplementedError()

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    async def run(self) -> str:
        try:
            return await self._run()
        except Exception as e:  # pylint: disable=W0718
            return gettext("Use tool failed: %s") % e

    async def _run(self) -> str:
        raise NotImplementedError()

    @classmethod
    def get_schema(cls) -> dict:
        return {
            "type": ToolType.FUNCTION.value,
            "function": {
                "name": cls.name,
                "description": cls.desc,
                "parameters": {
                    "type": "object",
                    "properties": cls.get_properties(),
                },
            },
        }

    @classmethod
    @abc.abstractmethod
    def get_properties(cls) -> dict:
        raise NotImplementedError()
