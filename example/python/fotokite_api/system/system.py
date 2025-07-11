import argparse
import json
import logging

import requests
from websockets.sync.client import connect

from fotokite_api.utils import BASE_REST_API_URL, BASE_WEBSOCKET_API_URL


def system_info() -> dict:
    """Fetches system information from the Fotokite REST API.

    Sends a GET request to the system info endpoint and returns the response as a dictionary.
    If the request fails or an exception occurs, logs the error and returns an empty dictionary.
    Useful for retrieving system identity and some of it's internal components.

    Returns:
        The system information retrieved from the API, or an empty dictionary on failure.
    """
    try:
        response = requests.get(f"{BASE_REST_API_URL}/info/system")
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching system info: {e}")

    return {}


def system_telemetry(on_message_callback, max_messages=None) -> None:
    """Subscribes to system telemetry via a WebSocket and processes incoming messages. Passes each message to the provided callback function.

    Args:
        on_message_callback: Function to be called with each telemetry message (parsed as a dict).
        max_messages: Maximum number of messages to process before disconnecting. If None, processes messages indefinitely.

    Raises:
        Exception: Logs any exception that occurs during the WebSocket connection or message processing.
    """
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


def _handle_telemetry(data) -> None:
    logging.info(f"Telemetry message received: {data}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

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
        logging.info(f"System Info: {info}")
    elif args.action == "telemetry":
        system_telemetry(_handle_telemetry)
