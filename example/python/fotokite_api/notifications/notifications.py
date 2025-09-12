import argparse
import json
import logging
import threading
import time
from typing import Callable, cast

import requests
from websockets.sync.client import connect

from fotokite_api.utils import (
    API_KEY,
    BASE_REST_API_URL,
    BASE_WEBSOCKET_API_URL,
    retrieve_auth_token,
)

Notification = dict[str, str]
notifications: dict[str, Notification] = {}


def dictionary(access_token: str) -> dict[str, object]:
    """Fetches the notifications dictionary.

    Args:
        access_token: The authentication token to use in the request.

    Returns:
        A dictionary containing notification definitions with their codes and descriptions.
        If the request fails or an exception occurs, logs the error and returns an empty dictionary.

    Raises:
        requests.HTTPError: If the HTTP request fails with a status code other than 200.
        Exception: For any other exceptions encountered during the request.
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{BASE_REST_API_URL}/info/notifications/dictionary", headers=headers
        )
        if response.status_code == 200:
            return cast(dict[str, object], response.json())
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching notifications dictionary: {e}")

    return {}


def notifications_telemetry(
    on_message_callback: Callable[[Notification], None],
    access_token: str,
    max_messages: int | None = None,
) -> None:
    """Subscribes to notifications telemetry.

    Args:
        on_message_callback: A callback function to handle incoming messages.
        access_token: The authentication token to use in the websocket connection.
        max_messages: The maximum number of messages to process. Defaults to None.
    """
    ws_url = f"{BASE_WEBSOCKET_API_URL}/telemetry/notifications/subscribe"
    try:
        with connect(
            ws_url, additional_headers={"Authorization": f"Bearer {access_token}"}
        ) as websocket:
            logging.info("Connected to notifications telemetry")
            count = 0
            while True:
                message = websocket.recv()
                data = json.loads(message)
                on_message_callback(data)

                count += 1
                if max_messages is not None and count >= max_messages:
                    break
    except Exception as e:
        logging.error(f"Error in notifications telemetry: {e}")


def _handle_notification(message: Notification) -> None:
    """Processes a notification, updating the global notifications store."""
    identifier = f"{message.get('code')}_{message.get('begin_time')}"
    end_time = message.get("end_time")

    if end_time:
        try:
            del notifications[identifier]
        except KeyError:
            pass
    else:
        notifications[identifier] = message


def log_notifications() -> None:
    """Periodically logs the current notifications every 5 seconds."""
    while True:
        time.sleep(5)
        if notifications:
            logging.info("Notifications:\n%s", json.dumps(notifications, indent=2))
        else:
            logging.info("No notifications at the moment")


def start_telemetry_with_logging(access_token: str) -> None:
    # Start the logger in a separate thread
    logging_thread = threading.Thread(target=log_notifications, daemon=True)
    logging_thread.start()
    # Start telemetry listening
    notifications_telemetry(_handle_notification, access_token)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Fotokite API Notifications Example")
    parser.add_argument(
        "--action",
        choices=["dictionary", "telemetry"],
        default="dictionary",
        help="Choose which action to trigger",
    )
    args = parser.parse_args()

    actions: dict[str, Callable[[str], object]] = {
        "dictionary": lambda access_token: logging.info(
            f"Notifications Dictionary: {dictionary(access_token)}"
        ),
        "telemetry": start_telemetry_with_logging,
    }

    auth_token = retrieve_auth_token(API_KEY)
    if auth_token is None:
        logging.error("Failed to retrieve authentication token. Exiting.")
        exit(1)

    action = actions.get(args.action)
    if action:
        action(auth_token)
    else:
        logging.error("Invalid action selected. Please choose a valid option.")
