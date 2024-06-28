import sys

from django.utils.translation import gettext_lazy
from ovinc_client.core.models import IntegerChoices, TextChoices

MESSAGE_MIN_LENGTH = 1
TEMPERATURE_DEFAULT = 1
TEMPERATURE_MIN = 0
TEMPERATURE_MAX = 2
TOP_P_DEFAULT = 0.5
TOP_P_MIN = 0

AI_API_REQUEST_TIMEOUT = 10 * 60

PRICE_DIGIT_NUMS = 20
PRICE_DECIMAL_NUMS = 10

if "celery" in sys.argv:
    TOKEN_ENCODING = ""
else:
    import tiktoken

    TOKEN_ENCODING = tiktoken.encoding_for_model("gpt-3.5-turbo")


class OpenAIRole(TextChoices):
    """
    OpenAI Chat Role
    """

    USER = "user", gettext_lazy("User")
    SYSTEM = "system", gettext_lazy("System")
    ASSISTANT = "assistant", gettext_lazy("Assistant")


class GeminiRole(TextChoices):
    """
    Gemini Chat Role
    """

    USER = "user", gettext_lazy("User")
    MODEL = "model", gettext_lazy("Model")


class BaiLianRole(TextChoices):
    """
    Bai Lian Chat Role
    """

    USER = "user", gettext_lazy("User")
    BOT = "bot", gettext_lazy("Bot")


class AIModelProvider(TextChoices):
    """
    AI Model Provider
    """

    OPENAI = "openai", gettext_lazy("Open AI")
    GOOGLE = "google", gettext_lazy("Google")
    BAIDU = "baidu", gettext_lazy("Baidu")
    TENCENT = "tencent", gettext_lazy("Tencent")
    ALIYUN = "aliyun", gettext_lazy("Aliyun")
    MOONSHOT = "moonshot", gettext_lazy("Moonshot")


class VisionSize(TextChoices):
    """
    Vision Size
    """

    S1024 = "1024x1024", gettext_lazy("1024x1024")


class VisionQuality(TextChoices):
    """
    Vision Quality
    """

    STANDARD = "standard", gettext_lazy("Standard")
    HD = "hd", gettext_lazy("HD")


class VisionStyle(TextChoices):
    """
    Vision Style
    """

    VIVID = "vivid", gettext_lazy("Vivid")
    NATURAL = "natural", gettext_lazy("Natural")


class CurrencyUnit(TextChoices):
    """
    Currency Unit
    """

    USD = "$", gettext_lazy("USD($)")
    RMB = "¥", gettext_lazy("RMB(¥)")


class HunyuanLogoControl(IntegerChoices):
    """
    Hunyuan Logo Control
    """

    ADD = 1, gettext_lazy("Add AI Logo")
    REMOVE = 0, gettext_lazy("Remove AI Logo")


class HunyuanReviseControl(IntegerChoices):
    """
    Hunyuan Revise Prompt Control
    """

    ENABLED = 1, gettext_lazy("Enabled")
    DISABLED = 0, gettext_lazy("Disabled")


class HunyuanJobStatusCode(TextChoices):
    """
    Hunyuan Job Status Code
    """

    WAITING = 1, gettext_lazy("Waiting")
    RUNNING = 2, gettext_lazy("Running")
    FAILED = 4, gettext_lazy("Failed")
    FINISHED = 5, gettext_lazy("Finished")


HUNYUAN_SUCCESS_DETAIL = "Success"
