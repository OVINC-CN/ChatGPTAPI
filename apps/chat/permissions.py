from rest_framework.permissions import BasePermission

from apps.chat.exceptions import NoModelPermission
from apps.chat.models import AIModel
from apps.wallet.exceptions import NoBalanceException
from apps.wallet.models import Wallet


class AIModelPermission(BasePermission):
    """
    AI Model Permission
    """

    # pylint: disable=W0236
    def has_permission(self, request, view):
        allowed = AIModel.check_user_permission(request.user, model=str(request.data.get("model", "")))
        if not allowed:
            raise NoModelPermission()
        balance = self.load_balance(request=request)
        if balance > 0:
            return True
        raise NoBalanceException()

    def load_balance(self, request) -> float:
        try:
            return Wallet.objects.get(user=request.user).balance
        except Wallet.DoesNotExist:  # pylint: disable=E1101
            return 0
