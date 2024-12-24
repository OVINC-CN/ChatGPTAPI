from django.utils.translation import gettext_lazy
from ovinc_client.core.models import IntegerChoices

TEXT_AUDIT_BATCH_SIZE = 10000


class TextAuditCallbackType(IntegerChoices):
    ALL = 1, gettext_lazy("Full Text")
    SENSITIVE = 2, gettext_lazy("Sensitive Text")


class AuditResult(IntegerChoices):
    NORMAL = 0, gettext_lazy("Normal")
    SENSITIVE = 1, gettext_lazy("Sensitive")
    ABNORMAL = 2, gettext_lazy("Abnormal")
