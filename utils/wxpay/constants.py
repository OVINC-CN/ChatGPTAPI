from django.utils.translation import gettext_lazy
from ovinc_client.core.models import TextChoices

WXPAY_CERT_CACHE_KEY = "wxpay_cert:{serial_no}"


class TradeStatus(TextChoices):
    """
    Trade Status
    """

    SUCCESS = "SUCCESS", gettext_lazy("Success")
    REFUND = "REFUND", gettext_lazy("Refund")
    NOTPAY = "NOTPAY", gettext_lazy("Not Pay")
    CLOSED = "CLOSED", gettext_lazy("Closed")
    REVOKED = "REVOKED", gettext_lazy("Revoked")
    USERPAYING = "USERPAYING", gettext_lazy("User Paying")
    PAYERROR = "PAYERROR", gettext_lazy("Pay Error")
