import base64
import hashlib
import ipaddress
import socket
import ssl

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.base import Certificate


def verify_pinned_key(host: str, port: int, expected_pin: str) -> None:
    """
    Verifies the server public key matches the pinned SHA256 hash.
    Allows connection via IP address even if the certificate only
    contains hostnames, provided the Public Key Pin matches.
    """
    if expected_pin.startswith("sha256//"):
        expected_pin = expected_pin[len("sha256//") :]

    cert = retrieve_server_certificate(host, port)

    validate_hostname(host, cert)
    verify_public_key_pin(host, expected_pin, cert)


def validate_hostname(host: str, cert: x509.Certificate) -> None:
    is_ip = False
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False

    if not is_ip:
        found_names = []
        try:
            # Modern standard: check SAN
            ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            found_names = ext.value.get_values_for_type(x509.DNSName)
        except x509.ExtensionNotFound:
            # Fallback: just check Common Name. Should not be needed with our certificates..
            common_names = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
            if common_names:
                found_names = [str(common_names[0].value)]

        if host not in found_names:
            raise RuntimeError(
                f"Hostname mismatch! Client expected '{host}', but certificate "
                f"only matches: {found_names}"
            )


def verify_public_key_pin(host: str, expected_pin: str, cert: x509.Certificate) -> None:
    pubkey = cert.public_key()
    pubkey_der = pubkey.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    digest = hashlib.sha256(pubkey_der).digest()
    actual_pin = base64.b64encode(digest).decode()

    if actual_pin != expected_pin:
        raise RuntimeError(
            f"Pinned key mismatch! \nExpected: {expected_pin}\nGot: {actual_pin}"
        )

    print(f"Successfully verified pinned key for {host}")


def retrieve_server_certificate(host: str, port: int) -> Certificate:
    # We have to create a context that ignores standard CA/Expiration checks.
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                der_cert = ssock.getpeercert(binary_form=True)
    except Exception as e:
        raise RuntimeError(f"Failed to establish SSL connection: {e}")

    if not der_cert:
        raise RuntimeError("Failed to retrieve server certificate")

    cert: Certificate = x509.load_der_x509_certificate(der_cert)

    print(f"Certificate for {host}:{port}")
    print(f"Subject: {cert.subject}")
    print(f"Issuer: {cert.issuer}")
    print(f"Valid From: {cert.not_valid_before_utc.isoformat()}")
    print(f"Valid To: {cert.not_valid_after_utc.isoformat()}")

    return cert
