from typing import Union

from django.core.cache import cache
from rest_framework.request import Request

from core.constants import DEFAULT_CACHE_TIMEOUT
from core.models import Empty
from core.utils import get_md5


class CacheItem:
    """
    cache item
    """

    def __init__(self, name: str, timeout: int, request: Request, user_bind: bool = True, *args, **kwargs) -> None:
        self.name = name
        self.timeout = timeout
        self.request = request
        self.user_bind = user_bind
        self.args = args
        self.kwargs = kwargs

    @property
    def username(self):
        if self.user_bind:
            return self.request.user.username
        return ""

    @property
    def cache_key(self) -> str:
        """
        cache key
        """

        return "{}:{}:{}".format(
            self.name,
            self.username,
            get_md5(
                [
                    get_md5(self.request.query_params),
                    get_md5(self.request.data),
                    get_md5(self.args),
                    get_md5(self.kwargs),
                ]
            ),
        )

    def set_cache(self, data: Union[list, dict]) -> None:
        """
        set cache
        """

        cache.set(self.cache_key, data, timeout=self.timeout)

    def get_cache(self) -> (bool, Union[list, dict]):
        """
        get cache
        """

        data = cache.get(self.cache_key, default=Empty())
        return not isinstance(data, Empty), data


class CacheMixin:
    """
    cache mixin for view set
    """

    enable_cache = False
    cache_user_bind = True
    cache_item_class = CacheItem
    cache_timeout = DEFAULT_CACHE_TIMEOUT

    def _build_cache_item(self, request: Request, *args, **kwargs) -> CacheItem:
        """
        build cache item from request
        """

        return self.cache_item_class(
            name=self.__class__.__name__,
            timeout=self.cache_timeout,
            request=request,
            user_bind=self.cache_user_bind,
            *args,
            **kwargs
        )

    def get_cache(self, request: Request, *args, **kwargs) -> (bool, Union[list, dict]):
        """
        get cache
        """

        cache_item = self._build_cache_item(request, *args, **kwargs)
        return cache_item.get_cache()

    def set_cache(self, data: Union[list, dict], request: Request, *args, **kwargs) -> None:
        """
        save data to cache
        """

        cache_item = self._build_cache_item(request, *args, **kwargs)
        cache_item.set_cache(data)
