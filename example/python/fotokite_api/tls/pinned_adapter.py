import base64
import hashlib
import ssl
from typing import Any, Mapping

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from requests import PreparedRequest, Response
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPSConnection
from urllib3.connectionpool import HTTPSConnectionPool
from urllib3.poolmanager import PoolManager


class _PinnedHTTPSConnection(HTTPSConnection):
    """
    Verifies the server's public-key pin immediately after the TLS handshake,
    before any HTTP data is written to the socket.
    """

    _expected_pin: str = ""

    def connect(self) -> None:
        super().connect()
        self._assert_pin()

    def _assert_pin(self) -> None:
        ssl_sock = self.sock
        if not isinstance(ssl_sock, ssl.SSLSocket):
            raise RuntimeError("Expected an SSLSocket after connect()")

        der = ssl_sock.getpeercert(binary_form=True)
        if not der:
            raise RuntimeError("No peer certificate on live socket")

        cert = x509.load_der_x509_certificate(der)
        pub_der = cert.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        actual = base64.b64encode(hashlib.sha256(pub_der).digest()).decode()

        if actual != self._expected_pin:
            raise RuntimeError(
                f"Public-key pin mismatch!\n"
                f"  expected : {self._expected_pin}\n"
                f"  got      : {actual}"
            )


class _PinnedHTTPSConnectionPool(HTTPSConnectionPool):
    def __init__(
        self, host: str, port: int | None = None, *, expected_pin: str, **kwargs: Any
    ) -> None:
        self.ConnectionCls = type(
            "_PinnedConn",
            (_PinnedHTTPSConnection,),
            {"_expected_pin": expected_pin},
        )
        super().__init__(host, port, **kwargs)


class _PinnedPoolManager(PoolManager):
    def __init__(self, *args: Any, expected_pin: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._expected_pin = expected_pin

    def _new_pool(
        self,
        scheme: str,
        host: str,
        port: int,
        request_context: dict[str, Any] | None = None,
    ) -> HTTPSConnectionPool:
        if scheme == "https":
            return _PinnedHTTPSConnectionPool(
                host, port, expected_pin=self._expected_pin
            )
        return super()._new_pool(scheme, host, port, request_context)  # type: ignore[return-value]


class PinnedPublicKeyAdapter(HTTPAdapter):
    """
    Drop-in requests adapter for SHA-256 public-key pinning.

    Pin verification happens on the **same TLS connection** used for the HTTP
    request — immediately after the handshake, before any data is sent.

    Usage:
        session.mount("https://", PinnedPublicKeyAdapter("sha256//<base64>"))
        resp = session.get("https://{gs_name}.fotokite-system.com/v1/system/info", ...)
    """

    def __init__(self, expected_pin: str, **kwargs: Any) -> None:
        if expected_pin.startswith("sha256//"):
            expected_pin = expected_pin[len("sha256//") :]
        self._expected_pin = expected_pin
        super().__init__(**kwargs)

    def init_poolmanager(
        self, connections: Any, maxsize: Any, block: Any = False, **pool_kwargs: Any
    ) -> None:
        self.poolmanager = _PinnedPoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            expected_pin=self._expected_pin,
            **pool_kwargs,
        )

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: float | tuple[float, float] | tuple[float, None] | None = None,
        verify: bool | str = True,
        cert: bytes | str | tuple[bytes | str, bytes | str] | None = None,
        proxies: Mapping[str, str] | None = None,
    ) -> Response:
        return super().send(
            request,
            stream=stream,
            timeout=timeout,
            verify=False,
            cert=cert,
            proxies=proxies,
        )
