import argparse
import json
import logging
from typing import Callable, cast

import requests
from websockets.sync.client import connect

from fotokite_api.utils import BASE_REST_API_URL, BASE_WEBSOCKET_API_URL, retrieve_auth_token, API_KEY

SystemMessage = dict[str, object]


def system_info(access_token: str = "") -> SystemMessage:
    try:
        response = requests.get(f"{BASE_REST_API_URL}/info/system", headers={"Authorization": f"Bearer {access_token}"})
        if response.status_code == 200:
            return cast(SystemMessage, response.json())
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching system info: {e}")

    return {}


def system_telemetry(
    on_message_callback: Callable[[SystemMessage], None],
    max_messages: int | None = None,
    access_token: str = ""
) -> None:
    ws_url = f"{BASE_WEBSOCKET_API_URL}/telemetry/system/subscribe?access_token={access_token}"
    try:
        with connect(ws_url, additional_headers={"Authorization": f"Bearer {access_token}"}) as websocket:
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
    args = parser.parse_args()

    auth_token = retrieve_auth_token(API_KEY)
    if auth_token is None:
        logging.error("Failed to retrieve authentication token. Exiting.")
        exit(1)

    if args.action == "info":
        info = system_info(auth_token)
        logging.info("System Info:\n%s", json.dumps(info, indent=2))
    elif args.action == "telemetry":
        system_telemetry(_handle_telemetry, None, auth_token)
