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


class _BaseVerifyOverrideAdapter(HTTPAdapter):
    """
    Base adapter that disables CA chain verification and injects arbitrary
    kwargs into the urllib3 pool manager (e.g. assert_fingerprint, assert_hostname).
    Subclasses just populate _pool_kwargs
    """

    _pool_kwargs: dict[str, Any]

    def init_poolmanager(
        self, connections: Any, maxsize: Any, block: Any = False, **pool_kwargs: Any
    ) -> None:
        pool_kwargs.update(self._pool_kwargs)
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)  # type: ignore

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


class PinnedPublicKeyAdapter(_BaseVerifyOverrideAdapter):
    """
    Drop-in requests adapter for SHA-256 public-key pinning.

    Pin verification happens on the same TLS connection used for the HTTP
    request immediately after the handshake, before any data is sent.

    Survives certificate renewal as long as the same key pair is reused.

    Usage:
        session.mount("https://", PinnedPublicKeyAdapter("sha256//<base64>"))
        session.get("https://192.168.2.100/v1/system/info")
    """

    def __init__(self, expected_pin: str, **kwargs: Any) -> None:
        if expected_pin.startswith("sha256//"):
            expected_pin = expected_pin[len("sha256//") :]
        self._expected_pin = expected_pin
        self._pool_kwargs = {}
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


class CertFingerprintAdapter(_BaseVerifyOverrideAdapter):
    """
    Pins against the server certificate's SHA-256 fingerprint using urllib3's
    built-in assert_fingerprint mechanism.

    Unlike public-key pinning, the fingerprint changes on every certificate
    renewal.

    Accepts colon separated hex (AA:BB:CC:...) or raw base64.

    Usage:
        session.mount("https://", CertFingerprintAdapter("AA:BB:CC:..."))
        session.get("https://192.168.2.100/v1/system/info")
    """

    def __init__(self, fingerprint: str, **kwargs: Any) -> None:
        self._pool_kwargs = {"assert_fingerprint": fingerprint}
        super().__init__(**kwargs)


class WildcardHostnameAdapter(_BaseVerifyOverrideAdapter):
    """
    Validates the certificate against a specific hostname regardless of what
    is in the URL, enabling wildcard matching for *.sigma.fotokite-system.com
    when connecting directly by IP, without a DNS override.

    SNI still uses the host from the URL, which is fine for single cert devices.

    Usage:
        session.mount("https://", WildcardHostnameAdapter("g028b.sigma.fotokite-system.com"))
        session.get("https://192.168.2.100/v1/system/info")
    """

    def __init__(self, assert_hostname: str, **kwargs: Any) -> None:
        self._pool_kwargs = {"assert_hostname": assert_hostname}
        super().__init__(**kwargs)
