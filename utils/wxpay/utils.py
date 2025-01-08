# pylint: disable=R0401

import base64
import datetime
import json
import math
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.x509 import load_pem_x509_certificate
from django.conf import settings
from django.core.cache import cache
from django_redis.client import DefaultClient
from ovinc_client.core.utils import uniq_id_without_time

from utils.wxpay.constants import WXPAY_CERT_CACHE_KEY
from utils.wxpay.exceptions import WxPayCertNotFound, WxPayInsecureResponse
from utils.wxpay.models import WXPayCert

trader_cert: WXPayCert
if settings.WXPAY_ENABLED:
    # load private key
    with open(settings.WXPAY_PRIVATE_KEY_PATH, "rb") as file:
        trader_cert = WXPayCert(
            serial_no=settings.WXPAY_PRIVATE_KEY_SERIAL_NO,
            private_key=serialization.load_pem_private_key(file.read(), password=None, backend=default_backend()),
        )

cache: DefaultClient


class WXPaySignatureTool:
    """
    Generic signature
    """

    @classmethod
    def generate(cls, request_method: str, request_url: str, request_body: dict) -> str:
        """
        Generate signature for WXPay API
        """

        request_path = "/" + request_url.split("/", 3)[3]
        nonce = uniq_id_without_time()
        timestamp = int(time.time())
        raw_info = "{request_method}\n{request_url}\n{timestamp}\n{nonce}\n{request_body}\n".format(
            request_method=request_method,
            request_url=request_path,
            timestamp=timestamp,
            nonce=nonce,
            request_body=json.dumps(request_body, ensure_ascii=False, separators=(",", ":")) if request_body else "",
        )
        signature = trader_cert.private_key.sign(
            data=raw_info.encode("utf-8"),
            padding=PKCS1v15(),
            algorithm=SHA256(),
        )
        b64_sign = base64.b64encode(signature).decode("utf-8")
        return (
            "{auth_type} "
            'mchid="{mchid}",'
            'serial_no="{serial_no}",'
            'nonce_str="{nonce_str}",'
            'timestamp="{timestamp}",'
            'signature="{b64_sign}"'
        ).format(
            auth_type=settings.WXPAY_AUTH_TYPE,
            mchid=settings.WXPAY_MCHID,
            serial_no=trader_cert.serial_no,
            nonce_str=nonce,
            timestamp=timestamp,
            b64_sign=b64_sign,
        )

    @classmethod
    def verify(cls, headers: dict, content: bytes) -> None:
        """
        Verify Request is from WXPay
        """

        raw_info = "{timestamp}\n{nonce}\n{content}\n".format(
            timestamp=headers.get("wechatpay-timestamp"),
            nonce=headers.get("wechatpay-nonce"),
            content=content.decode(),
        )
        signature = base64.b64decode(headers.get("wechatpay-signature", "").encode())
        wxpay_cert = cls.load_wxpay_cert(serial_no=headers.get("wechatpay-serial", ""))
        try:
            wxpay_cert.public_key.verify(
                signature=signature, data=raw_info.encode(), padding=PKCS1v15(), algorithm=SHA256()
            )
        except InvalidSignature as err:
            raise WxPayInsecureResponse() from err

    @classmethod
    def load_wxpay_cert(cls, serial_no: str) -> WXPayCert:
        """
        Load WXPay Cert
        """

        # load from cache
        cached_key: bytes = cache.get(key=WXPAY_CERT_CACHE_KEY.format(serial_no=serial_no), default="")
        if cached_key:
            return WXPayCert(serial_no=serial_no, public_key=load_pem_x509_certificate(data=cached_key).public_key())

        # load from wxpay api
        # pylint: disable=C0415
        from utils.wxpay.api import GetCerts

        # load cert
        cert_data: dict = GetCerts().request()
        for cert in cert_data["data"]:
            # check serial id
            if not cert["serial_no"] == serial_no:
                continue
            # decrypt cert
            plaintext = cls.decrypt(
                nonce=cert["encrypt_certificate"]["nonce"].encode(),
                data=base64.b64decode(cert["encrypt_certificate"]["ciphertext"].encode()),
                associated_data=cert["encrypt_certificate"]["associated_data"].encode(),
            )
            # save cache
            expire_time = datetime.datetime.strptime(cert["expire_time"], settings.WXPAY_TIME_FORMAT)
            cache.set(
                key=WXPAY_CERT_CACHE_KEY.format(serial_no=serial_no),
                value=plaintext,
                timeout=min(
                    settings.WXPAY_CERT_TIMEOUT,
                    math.floor((expire_time - datetime.datetime.now(tz=expire_time.tzinfo)).total_seconds()),
                ),
            )
            return WXPayCert(serial_no=serial_no, public_key=load_pem_x509_certificate(data=plaintext).public_key())

        raise WxPayCertNotFound()

    @classmethod
    def decrypt(cls, nonce: bytes, data: bytes, associated_data: bytes) -> bytes:
        """
        Decrypt Data
        """

        aesgcm = AESGCM(settings.WXPAY_API_V3_KEY.encode())
        return aesgcm.decrypt(nonce=nonce, data=data, associated_data=associated_data)
