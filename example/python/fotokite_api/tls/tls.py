import argparse
import json
import logging
from urllib.parse import urlparse

import requests
import urllib3

from fotokite_api.tls.adapter import (
    CertFingerprintAdapter,
    PinnedPublicKeyAdapter,
    WildcardHostnameAdapter,
)
from fotokite_api.utils import (
    BASE_HTTPS_REST_API_URL,
    retrieve_auth_token,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def request_using_tls_hostname(hostname: str, access_token: str = "") -> None:
    """Connects via hostname — standard CA chain + expiry validation."""
    if not access_token or not hostname:
        logging.error("Hostname and access token are required for this action.")
        return

    try:
        response = requests.get(
            f"https://{hostname}/system/info",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 200:
            logging.info(f"System info: {json.dumps(response.json(), indent=2)}")
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching system info: {e}")


def request_using_pinned_down_public_key(
    public_key: str, access_token: str = ""
) -> None:
    """
    Pins against the server's public key (SPKI SHA-256).
    Survives cert renewal if the same key pair is reused.
    """
    if not access_token or not public_key:
        logging.error("Public key and access token are required.")
        return

    try:
        session = requests.Session()
        session.mount("https://", PinnedPublicKeyAdapter(public_key))

        response = session.get(
            f"{BASE_HTTPS_REST_API_URL}/system/info",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        logging.info(f"System info: {json.dumps(response.json(), indent=2)}")

    except Exception as e:
        logging.error(f"TLS pin verification failed: {e}")


def request_using_cert_fingerprint(fingerprint: str, access_token: str = "") -> None:
    """
    Pins against the whole certificate's SHA-256 fingerprint.
    Changes on every cert renewal — best for controlled/short-lived deployments.
    """
    if not access_token or not fingerprint:
        logging.error("Fingerprint and access token are required.")
        return

    try:
        session = requests.Session()
        session.mount("https://", CertFingerprintAdapter(fingerprint))

        response = session.get(
            f"{BASE_HTTPS_REST_API_URL}/system/info",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        logging.info(f"System info: {json.dumps(response.json(), indent=2)}")

    except Exception as e:
        logging.error(f"TLS fingerprint verification failed: {e}")


def request_using_wildcard_hostname(
    gs_ip: str, gs_hostname: str, access_token: str = ""
) -> None:
    """
    Validates the cert against gs_hostname (matching *.sigma.fotokite-system.com)
    but connects via IP if provided, avoiding DNS. Falls back to hostname if no IP.
    """
    if not access_token or not gs_hostname:
        logging.error("Hostname and access token are required.")
        return

    try:
        session = requests.Session()
        session.mount("https://", WildcardHostnameAdapter(gs_hostname))

        parsed = urlparse(BASE_HTTPS_REST_API_URL)
        host = gs_ip if gs_ip else gs_hostname
        base_url = parsed._replace(
            netloc=f"{host}:{parsed.port}" if parsed.port else host
        ).geturl()

        response = session.get(
            f"{base_url}/system/info",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        logging.info(f"System info: {json.dumps(response.json(), indent=2)}")

    except Exception as e:
        logging.error(f"Wildcard hostname verification failed: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Fotokite API TLS Example")
    parser.add_argument(
        "--action",
        choices=["hostname", "pinned_key", "cert_fingerprint", "wildcard_hostname"],
        default="hostname",
        help="Choose which TLS verification strategy to use",
    )
    parser.add_argument(
        "--hostname",
        default="",
        help="GS name (e.g. g028b) or full hostname for wildcard mode",
    )
    parser.add_argument(
        "--gs_ip",
        default="",
        help="IP address of the GS for wildcard_hostname mode",
    )
    parser.add_argument(
        "--public_key",
        default="",
        help="Pinned public key SHA-256 (base64 or sha256//<base64>)",
    )
    parser.add_argument(
        "--fingerprint",
        default="",
        help="SHA-256 cert fingerprint (AA:BB:... or base64)",
    )
    parser.add_argument(
        "--secret",
        default="",
        help="Authentication secret to use",
    )
    parser.add_argument(
        "--secret_type",
        choices=["key", "token"],
        default="key",
        help="Whether to use an API Key for token issuance or directly a token",
    )
    args = parser.parse_args()

    auth_token = retrieve_auth_token(args.secret, args.secret_type)
    if auth_token is None:
        logging.error("Failed to retrieve authentication token. Exiting.")
        exit(1)

    if args.action == "hostname":
        request_using_tls_hostname(args.hostname, auth_token)
    elif args.action == "pinned_key":
        request_using_pinned_down_public_key(args.public_key, auth_token)
    elif args.action == "cert_fingerprint":
        request_using_cert_fingerprint(args.fingerprint, auth_token)
    elif args.action == "wildcard_hostname":
        request_using_wildcard_hostname(args.gs_ip, args.hostname, auth_token)
