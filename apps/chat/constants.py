import re
from dataclasses import dataclass

from django.utils.translation import gettext_lazy
from ovinc_client.core.models import TextChoices

MESSAGE_MIN_LENGTH = 1
TEMPERATURE_DEFAULT = 1
TEMPERATURE_MIN = 0
TEMPERATURE_MAX = 2
TOP_P_DEFAULT = 1
TOP_P_MIN = 0

PRICE_DIGIT_NUMS = 20
PRICE_DECIMAL_NUMS = 10

HUNYUAN_DATA_PATTERN = re.compile(rb"data:\s\{.*\}\n\n")


class OpenAIRole(TextChoices):
    """
    OpenAI Chat Role
    """

    USER = "user", gettext_lazy("User")
    SYSTEM = "system", gettext_lazy("System")
    ASSISTANT = "assistant", gettext_lazy("Assistant")


class OpenAIModel(TextChoices):
    """
    OpenAI Model
    """

    GPT35_Turbo = "gpt-3.5-turbo", "GPT3.5 Turbo"
    GPT35_Turbo_0613 = "gpt-3.5-turbo-0613", "GPT3.5 Turbo (0613)"
    GPT35_Turbo_16K = "gpt-3.5-turbo-16k", "GPT3.5 Turbo (16K)"
    GPT35_Turbo_16K_0613 = "gpt-3.5-turbo-16k-0613", "GPT3.5 Turbo (16K, 0613)"
    GPT4 = "gpt-4", "GPT4"
    GPT4_0613 = "gpt-4-0613", "GPT4 (0613)"
    GPT4_32K = "gpt-4-32k", "GPT4 (32K)"
    GPT4_32K_0613 = "gpt-4-32k-0613", "GPT4 (32K, 0613)"
    HUNYUAN = "hunyuan-plus", gettext_lazy("HunYuan Plus")

    @classmethod
    def get_name(cls, model: str) -> str:
        for value, label in cls.choices:
            if value == model:
                return str(label)
        return model


@dataclass
class OpenAIUnitPriceItem:
    """
    OpenAI Unit Price Item
    """

    prompt_token_unit_price: float
    completion_token_unit_price: float


class OpenAIUnitPrice:
    """
    OpenAI Unit Price Per Thousand Tokens ($)
    """

    price_map = {
        OpenAIModel.GPT4.value: OpenAIUnitPriceItem(0.03, 0.06),
        OpenAIModel.GPT4_0613.value: OpenAIUnitPriceItem(0.03, 0.06),
        OpenAIModel.GPT4_32K.value: OpenAIUnitPriceItem(0.06, 0.12),
        OpenAIModel.GPT4_32K_0613.value: OpenAIUnitPriceItem(0.06, 0.12),
        OpenAIModel.GPT35_Turbo.value: OpenAIUnitPriceItem(0.0015, 0.002),
        OpenAIModel.GPT35_Turbo_0613.value: OpenAIUnitPriceItem(0.0015, 0.002),
        OpenAIModel.GPT35_Turbo_16K.value: OpenAIUnitPriceItem(0.003, 0.004),
        OpenAIModel.GPT35_Turbo_16K_0613.value: OpenAIUnitPriceItem(0.003, 0.004),
        OpenAIModel.HUNYUAN.value: OpenAIUnitPriceItem(0.10 / 7, 0.10 / 7),
    }

    @classmethod
    def get_price(cls, model: str) -> OpenAIUnitPriceItem:
        return cls.price_map.get(model)
