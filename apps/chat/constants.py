import re
import sys

from django.utils.translation import gettext_lazy
from ovinc_client.core.models import TextChoices

MESSAGE_MIN_LENGTH = 1
TEMPERATURE_DEFAULT = 1
TEMPERATURE_MIN = 0
TEMPERATURE_MAX = 2
TOP_P_DEFAULT = 1
TOP_P_MIN = 0

AI_API_REQUEST_TIMEOUT = 10 * 60

PRICE_DIGIT_NUMS = 20
PRICE_DECIMAL_NUMS = 10

HUNYUAN_DATA_PATTERN = re.compile(rb"data:\s\{.*\}\n\n")

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


class AIModelProvider(TextChoices):
    """
    AI Model Provider
    """

    OPENAI = "openai", gettext_lazy("Open AI")
    GOOGLE = "google", gettext_lazy("Google")
    BAIDU = "baidu", gettext_lazy("Baidu")
    TENCENT = "tencent", gettext_lazy("Tencent")


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
