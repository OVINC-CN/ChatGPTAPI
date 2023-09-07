from django.conf import settings
from django.utils.translation import gettext_lazy

from core.models import TextChoices


class UserCacheKey:
    """
    User Cache Key
    """

    SESSION_USER = "session-user:{username}"
    SESSION_USER_TIMEOUT = settings.SESSION_COOKIE_AGE


class UserTypeChoices(TextChoices):
    """
    User Type Choices
    """

    PERSONAL = "personal", gettext_lazy("Personal")
    PLATFORM = "platform", gettext_lazy("Platform")


class UserPropertyChoices(TextChoices):
    """
    User Property
    """

    AVATAR = "avatar", gettext_lazy("Avatar")
    PHONE_NUMBER = "phone_number", gettext_lazy("Phone Number")
    MAIL_ADDRESS = "mail_address", gettext_lazy("Mail Address")
