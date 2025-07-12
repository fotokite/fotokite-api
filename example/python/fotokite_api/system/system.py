import argparse
import json
import logging
from typing import Callable, cast

import requests
from websockets.sync.client import connect

from fotokite_api.utils import BASE_REST_API_URL, BASE_WEBSOCKET_API_URL

SystemMessage = dict[str, object]


def system_info() -> SystemMessage:
    try:
        response = requests.get(f"{BASE_REST_API_URL}/info/system")
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
) -> None:
    ws_url = f"{BASE_WEBSOCKET_API_URL}/telemetry/system/subscribe"
    try:
        with connect(ws_url) as websocket:
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

    if args.action == "info":
        info = system_info()
        logging.info("System Info:\n%s", json.dumps(info, indent=2))
    elif args.action == "telemetry":
        system_telemetry(_handle_telemetry)
