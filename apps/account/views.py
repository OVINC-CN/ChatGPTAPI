from django.contrib import auth
from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.account.exceptions import VerifyFailed
from apps.account.models import User
from apps.account.serializers import UserInfoSerializer, UserSignInSerializer
from core.auth import OAuthBackend, SessionAuthenticate
from core.viewsets import ListMixin, MainViewSet

USER_MODEL: User = get_user_model()


class UserInfoViewSet(ListMixin, MainViewSet):
    """
    User Info
    """

    queryset = USER_MODEL.objects.all()

    def list(self, request, *args, **kwargs):
        """
        User Info
        """

        return Response(UserInfoSerializer(request.user).data)


class UserSignViewSet(MainViewSet):
    """
    User Sign
    """

    queryset = USER_MODEL.objects.all()
    authentication_classes = [SessionAuthenticate]

    @action(methods=["POST"], detail=False)
    def sign_in(self, request, *args, **kwargs):
        """
        Sign In
        """

        # verify
        request_serializer = UserSignInSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # auth
        user = OAuthBackend().authenticate(request, code=request_data["code"])
        if user:
            auth.login(request, user)
            return Response()

        raise VerifyFailed()

    @action(methods=["GET"], detail=False)
    def sign_out(self, request, *args, **kwargs):
        """
        Sign Out
        """

        auth.logout(request)
        return Response()
