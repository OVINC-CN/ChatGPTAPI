from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.types import (
    CertificatePublicKeyTypes,
    PrivateKeyTypes,
)


@dataclass
class WXPayCert:
    serial_no: str
    private_key: Optional[PrivateKeyTypes] = None
    public_key: Optional[CertificatePublicKeyTypes] = None
