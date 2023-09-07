import json
from typing import Union

import requests
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.authentication import BaseAuthentication, SessionAuthentication

from core.constants import OVINC_APP_HEADER, OVINC_AUTH_URL, OVINC_TOKEN
from core.exceptions import LoginRequired
from core.logger import logger

USER_MODEL = get_user_model()


class SessionAuthenticate(SessionAuthentication):
    """
    Session Auth
    """

    def authenticate(self, request) -> Union[tuple, None]:
        # Get Auth Token
        auth_token = request.COOKIES.get(settings.AUTH_TOKEN_NAME, None)
        if not auth_token:
            return None
        # Verify Auth Token
        user = self.check_token(auth_token, request)
        if not user:
            return None
        return user, None

    def check_token(self, token, request) -> USER_MODEL:
        # Cache First
        user = cache.get(token)
        if user:
            return user
        # OSB Auth
        try:
            # Request
            result = requests.post(
                settings.OVINC_API_DOMAIN.rstrip("/") + OVINC_AUTH_URL,
                json={OVINC_TOKEN: token},
                headers={
                    OVINC_APP_HEADER: json.dumps({"app_code": settings.APP_CODE, "app_secret": settings.APP_SECRET})
                },
            ).json()
            # Create User
            if result.get("data") and result["data"].get("username"):
                username = result["data"]["username"]
                user = USER_MODEL.objects.get_or_create(username=username)[0]
                for key, val in result["data"].items():
                    setattr(user, key, val)
                user.save(update_fields=result["data"].keys())
                cache.set(token, user)
                auth.login(request=request, user=user)
                return self.check_token(token, request)
            else:
                logger.info("[OSBAuthFailed] Result => %s", result)
                return None
        except Exception as err:
            logger.exception(err)
            return None

    @classmethod
    def get_user(cls, pk: str) -> USER_MODEL:
        return USER_MODEL.objects.get(pk=pk)


class AuthTokenAuthenticate(BaseAuthentication):
    """
    Auth Token Authenticate
    """

    def authenticate(self, request) -> (USER_MODEL, None):
        # User Auth Token
        raise LoginRequired()
