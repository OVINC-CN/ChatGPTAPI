from cryptography.hazmat.primitives.asymmetric.types import (
    CertificatePublicKeyTypes,
    PrivateKeyTypes,
)
from pydantic import BaseModel as BaseDataModel
from pydantic import ConfigDict


class WXPayCert(BaseDataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    serial_no: str
    private_key: PrivateKeyTypes | None = None
    public_key: CertificatePublicKeyTypes | None = None
