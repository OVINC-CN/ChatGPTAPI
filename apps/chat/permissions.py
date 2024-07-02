from channels.db import database_sync_to_async
from rest_framework.permissions import BasePermission

from apps.wallet.exceptions import NoBalanceException
from apps.wallet.models import Wallet


class AIModelPermission(BasePermission):
    """
    AI Model Permission
    """

    # pylint: disable=W0236
    async def has_permission(self, request, view):
        balance = await self.load_balance(request=request)
        if balance > 0:
            return True
        raise NoBalanceException()

    @database_sync_to_async
    def load_balance(self, request) -> float:
        try:
            return Wallet.objects.get(user=request.user).balance
        except Wallet.DoesNotExist:  # pylint: disable=E1101
            return 0
