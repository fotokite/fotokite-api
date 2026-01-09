import argparse
import json
import logging
from typing import Callable, cast

import requests
from websockets.sync.client import connect

from fotokite_api.utils import (
    BASE_REST_API_URL,
    BASE_WEBSOCKET_API_URL,
    retrieve_auth_token,
)

SystemMessage = dict[str, object]


def system_info(access_token: str = "") -> SystemMessage:
    """Fetches system information.

    Args:
        access_token: Bearer token for API authentication. Defaults to "".

    Returns:
        Parsed system information message if the request is successful.
        Empty dictionary if an error occurs.

    Raises:
        requests.HTTPError: If the HTTP request fails with a non-200 status code.
        Exception: For any other exceptions encountered during the request.
    """
    try:
        response = requests.get(
            f"{BASE_REST_API_URL}/system/info",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 200:
            return cast(SystemMessage, response.json())
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching system info: {e}")

    return {}


def system_telemetry(
    on_message_callback: Callable[[SystemMessage], None],
    access_token: str = "",
    max_messages: int | None = None,
) -> None:
    """Subscribes to system info telemetry

    Args:
        on_message_callback: A callback function to handle incoming messages.
        access_token: The authentication token to use in the websocket connection.
        max_messages: The maximum number of messages to process. Defaults to None.
    """
    ws_url = (
        f"{BASE_WEBSOCKET_API_URL}/system/state/subscribe?access_token={access_token}"
    )
    try:
        with connect(
            ws_url, additional_headers={"Authorization": f"Bearer {access_token}"}
        ) as websocket:
            logging.info("Connected to system telemetry")
            count = 0
            while True:
                message = websocket.recv()
                data = json.loads(message)

                on_message_callback(data)

                count += 1
                if max_messages is not None and count >= max_messages:
                    break
    except Exception as e:
        logging.error(f"Error in system telemetry: {e}")


def _handle_telemetry(data: SystemMessage) -> None:
    logging.info(f"System telemetry message received:\n{json.dumps(data, indent=2)}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Fotokite API System Example")
    parser.add_argument(
        "--action",
        choices=["info", "telemetry"],
        default="info",
        help="Choose which action to trigger",
    )
    parser.add_argument(
        "--secret",
        default="",
        help="Authentication secret to use",
    )
    parser.add_argument(
        "--secret_type",
        choices=["key", "token"],
        default="",
        help="Whether to use an API Key for token issuance or directly a token on the request",
    )
    args = parser.parse_args()

    auth_token = retrieve_auth_token(args.secret, args.secret_type)
    if auth_token is None:
        logging.error("Failed to retrieve authentication token. Exiting.")
        exit(1)

    if args.action == "info":
        info = system_info(auth_token)
        logging.info("System Info:\n%s", json.dumps(info, indent=2))
    elif args.action == "telemetry":
        system_telemetry(_handle_telemetry, auth_token)
