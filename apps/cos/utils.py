import time
from hashlib import md5, sha256
from urllib.parse import (
    ParseResult,
    parse_qs,
    quote,
    unquote,
    urlencode,
    urlparse,
    urlunparse,
)

from django.conf import settings
from django.core.cache import cache
from django_redis.client import DefaultClient
from ovinc_client.core.utils import uniq_id_without_time

cache: DefaultClient


class TCloudUrlParser:
    """
    tcloud url parser
    """

    cos_url = urlparse(settings.QCLOUD_COS_URL)
    cache_key_format = "qcloud-cdn-sign:{url_hash}"

    def __init__(self, url: str) -> None:
        self._url = url
        self._parsed_url = self.parse_url()
        self._query_params = parse_qs(self._parsed_url.query)
        if self._parsed_url.hostname == self.cos_url.hostname:
            self.add_ci_param()
            self.add_cdn_signed_param()
            self._parsed_url = self._parsed_url._replace(query=urlencode(self._query_params, doseq=True))

    @property
    def url(self) -> str:
        return str(urlunparse(self._parsed_url))

    def parse_url(self) -> ParseResult:
        parsed_url = urlparse(self._url)
        if parsed_url.path == unquote(parsed_url.path):
            return parsed_url._replace(path=quote(parsed_url.path))
        return parsed_url

    def add_cdn_signed_param(self) -> None:
        if not self._url or not settings.QCLOUD_CDN_SIGN_KEY:
            return
        self._query_params[settings.QCLOUD_CDN_SIGN_KEY_URL_PARAM] = [
            self.sign(hostname=self._parsed_url.hostname, path=self._parsed_url.path)
        ]

    def add_ci_param(self) -> None:
        if not self._url or not settings.QCLOUD_COS_IMAGE_STYLE:
            return
        if self._parsed_url.path.rsplit(".", 1)[-1] in settings.QCLOUD_COS_IMAGE_SUFFIX:
            self._query_params[settings.QCLOUD_COS_IMAGE_STYLE] = [""]

    @classmethod
    def sign(cls, hostname: str, path: str) -> str:
        # load cache
        full_signature = cls.get_sign_cache(hostname=hostname, path=path)
        if full_signature:
            return full_signature
        # build new signature
        timestamp = int(time.time())
        nonce = uniq_id_without_time()
        uid = "0"
        signature = md5(f"{path}-{timestamp}-{nonce}-{uid}-{settings.QCLOUD_CDN_SIGN_KEY}".encode()).hexdigest()
        full_signature = f"{timestamp}-{nonce}-{uid}-{signature}"
        cls.set_sign_cache(hostname=hostname, path=path, full_signature=full_signature)
        return full_signature

    @classmethod
    def get_sign_cache(cls, hostname: str, path: str) -> str | None:
        return cache.get(key=cls.build_sign_cache_key(hostname=hostname, path=path))

    @classmethod
    def set_sign_cache(cls, hostname: str, path: str, full_signature: str) -> None:
        cache.set(
            key=cls.build_sign_cache_key(hostname=hostname, path=path),
            value=full_signature,
            timeout=settings.QCLOUD_CDN_SIGN_CACHE_TIMEOUT,
        )

    @classmethod
    def build_sign_cache_key(cls, hostname: str, path: str) -> str:
        return cls.cache_key_format.format(url_hash=sha256(f"{hostname}{path}".encode()).hexdigest())
