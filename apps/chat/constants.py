from django.utils.translation import gettext_lazy
from ovinc_client.core.models import IntegerChoices, TextChoices

MESSAGE_MIN_LENGTH = 1

PRICE_DIGIT_NUMS = 20
PRICE_DECIMAL_NUMS = 10

WS_CLOSED_KEY = "ws:closed:{}"

MESSAGE_CACHE_KEY = "message:{}"


class OpenAIRole(TextChoices):
    """
    OpenAI Chat Role
    """

    USER = "user", gettext_lazy("User")
    SYSTEM = "system", gettext_lazy("System")
    ASSISTANT = "assistant", gettext_lazy("Assistant")


class AIModelProvider(TextChoices):
    """
    AI Model Provider
    """

    OPENAI = "openai", gettext_lazy("Open AI")
    MIDJOURNEY = "midjourney", gettext_lazy("Midjourney")


class MidjourneyResult(TextChoices):
    """
    Midjourney Result
    """

    NOT_START = "NOT_START", gettext_lazy("Not Start")
    SUBMITTED = "SUBMITTED", gettext_lazy("Submitted")
    MODAL = "MODAL", gettext_lazy("Modal")
    IN_PROGRESS = "IN_PROGRESS", gettext_lazy("In Progress")
    FAILURE = "FAILURE", gettext_lazy("Failure")
    SUCCESS = "SUCCESS", gettext_lazy("Success")


class MessageContentType(TextChoices):
    """
    Message Content Type
    """

    TEXT = "text", gettext_lazy("Text")
    IMAGE_URL = "image_url", gettext_lazy("Image URL")
    IMAGE = "image", gettext_lazy("Image")


class SpanType(TextChoices):
    """
    Span Type
    """

    API = "api", gettext_lazy("API")
    CHUNK = "chunk", gettext_lazy("Chunk")
    FETCH = "fetch", gettext_lazy("Fetch")
    CHAT = "chat", gettext_lazy("Chat")
    AUDIT = "audit", gettext_lazy("Audit")


class MessageSyncAction(IntegerChoices):
    """
    Message Sync Action
    """

    UPDATE = 1, gettext_lazy("Update")
    DELETE = 2, gettext_lazy("Delete")
