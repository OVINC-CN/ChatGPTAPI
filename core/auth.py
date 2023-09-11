import json
from typing import Tuple, Union

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from rest_framework.authentication import SessionAuthentication

from core.constants import OVINC_APP_HEADER, OVINC_AUTH_URL, OVINC_TOKEN
from core.exceptions import LoginRequired
from core.logger import logger

USER_MODEL = get_user_model()


class SessionAuthenticate(SessionAuthentication):
    """
    Session Auth
    """

    def authenticate(self, request) -> Union[Tuple[USER_MODEL, None], None]:
        user = getattr(request._request, "user", None)
        if user is None or not user.is_active:
            return None
        return user, None


class LoginRequiredAuthenticate(SessionAuthenticate):
    """
    Login Required Authenticate
    """

    def authenticate(self, request) -> (USER_MODEL, None):
        user = super().authenticate(request)
        if user is None or not user[0].is_active:
            raise LoginRequired()
        return user


class OAuthBackend(BaseBackend):
    """
    OAuth
    """

    def authenticate(self, request, code: str = None, **kwargs):
        if not code:
            return
        # Union API Auth
        try:
            # Request
            result = requests.post(
                settings.OVINC_API_DOMAIN.rstrip("/") + OVINC_AUTH_URL,
                json={OVINC_TOKEN: code},
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
                return user
            else:
                logger.info("[UnionAuthFailed] Result => %s", result)
                return None
        except Exception as err:
            logger.exception(err)
            return None
