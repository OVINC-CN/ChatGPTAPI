from django.conf import settings
from django.conf.global_settings import LANGUAGE_COOKIE_NAME
from django.contrib.auth import get_user_model
from rest_framework.response import Response

from apps.account.models import User
from apps.home.serializers import I18nRequestSerializer
from core.auth import SessionAuthenticate
from core.viewsets import MainViewSet

USER_MODEL: User = get_user_model()


class HomeView(MainViewSet):
    """
    Home View
    """

    queryset = USER_MODEL.get_queryset()
    authentication_classes = [SessionAuthenticate]

    def list(self, request, *args, **kwargs):
        msg = f"[{request.method}] Connect Success"
        return Response({"resp": msg, "user": request.user.username})


class I18nViewSet(MainViewSet):
    """
    International
    """

    authentication_classes = [SessionAuthenticate]

    def create(self, request, *args, **kwargs):
        """
        Change Language
        """

        # Varify Request Data
        request_serializer = I18nRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # Change Lang
        lang_code = request_data["language"]
        response = Response()
        response.set_cookie(
            LANGUAGE_COOKIE_NAME,
            lang_code,
            max_age=settings.SESSION_COOKIE_AGE,
            domain=settings.SESSION_COOKIE_DOMAIN,
        )
        return response
