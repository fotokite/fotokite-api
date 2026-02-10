import argparse
import json
import logging
from urllib.parse import urlparse

import requests
import urllib3

from fotokite_api.tls.utils import verify_pinned_key
from fotokite_api.utils import (
    BASE_HTTPS_REST_API_URL,
    BASE_HTTPS_REST_API_URL_WITH_HOSTNAME,
    retrieve_auth_token,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def request_using_tls_hostname(hostname: str, access_token: str = "") -> None:
    """ """
    if not access_token or not hostname:
        logging.error("Hostname and access token are required for this action.")
        return

    try:
        response = requests.get(
            f"{BASE_HTTPS_REST_API_URL_WITH_HOSTNAME.format(hostname=hostname)}/v0/system/info",
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
    if not access_token or not public_key:
        logging.error("Public key and access token are required for this action.")
        return

    try:
        parsed = urlparse(BASE_HTTPS_REST_API_URL)
        host = parsed.hostname
        port = parsed.port or 443

        if not host:
            logging.error("Failed to parse host from the base URL.")
            return

        verify_pinned_key(host, port, public_key)

        # perform the actual request (skip normal TLS checks with verify=False)
        response: requests.Response = requests.get(
            f"{BASE_HTTPS_REST_API_URL}/system/info",
            headers={"Authorization": f"Bearer {access_token}"},
            verify=False,
        )

        if response.status_code == 200:
            logging.info(f"System info: {json.dumps(response.json(), indent=2)}")
        else:
            response.raise_for_status()

    except Exception as e:
        logging.error(f"Error fetching system info: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Fotokite API System Example")
    parser.add_argument(
        "--action",
        choices=["hostname", "pinned_key"],
        default="hostname",
        help="Choose which action to trigger",
    )
    parser.add_argument(
        "--hostname",
        default="",
        help="Hostname of the Fotokite system to connect to",
    )
    parser.add_argument(
        "--public_key",
        default="",
        help="Pinned public key of the Fotokite system to connect to",
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
        help="Whether to use an API Key for token issuance or directly a token on the request",
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
