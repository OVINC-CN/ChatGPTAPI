from rest_framework.permissions import BasePermission

from apps.chat.exceptions import NoModelPermission
from apps.chat.models import ModelPermission


class AIModelPermission(BasePermission):
    """
    AI Model Permission
    """

    def has_permission(self, request, view):
        model = request.data.get("model", "")
        if ModelPermission.authed_models(user=request.user, model=model).exists():
            return True
        raise NoModelPermission()
