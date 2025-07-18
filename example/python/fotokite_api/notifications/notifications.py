import argparse
import json
import logging
import threading
import time
from typing import Callable, cast

import requests
from websockets.sync.client import connect

from fotokite_api.utils import BASE_REST_API_URL, BASE_WEBSOCKET_API_URL

Notification = dict[str, str]
notifications: dict[str, Notification] = {}


def dictionary() -> dict[str, object]:
    """Fetches the notifications dictionary.

    Returns:
        A dictionary containing notification definitions with their codes and descriptions.
        If the request fails or an exception occurs, logs the error and returns an empty dictionary.

    Raises:
        requests.HTTPError: If the HTTP request fails with a status code other than 200.
        Exception: For any other exceptions encountered during the request.
    """
    try:
        response = requests.get(f"{BASE_REST_API_URL}/info/notifications/dictionary")
        if response.status_code == 200:
            return cast(dict[str, object], response.json())
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching notifications dictionary: {e}")

    return {}


def notifications_telemetry(
    on_message_callback: Callable[[Notification], None],
    max_messages: int | None = None,
    from_time: str | None = None,
) -> None:
    """Subscribes to notifications telemetry.

    Args:
        on_message_callback: A callback function to handle incoming messages.
        max_messages: The maximum number of messages to process. Defaults to None.
        from_time: The starting time for fetching messages. Defaults to None.
    """
    if from_time is None:
        now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        from_time = now

    ws_url = f"{BASE_WEBSOCKET_API_URL}/telemetry/notifications/subscribe"
    if from_time is not None:
        ws_url += f"?from_time={from_time}"
    try:
        with connect(ws_url) as websocket:
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
    """Processes a notification, updating the global notifications store.

    For each notification in the input message:
    - If the notification has an 'end_time', it removes the notification from the global store.
    - Otherwise, it adds or updates the notification in the global store using a unique identifier.
    - The identifier is constructed from the notification's 'code' and 'begin_time'.
    Used to keep track of current notifications and their statuses.

    Args:
        message: A dictionary representing a notification message.
    """
    identifier = f"{message.get("code")}_{message.get("begin_time")}"
    end_time = message.get("end_time")

    if end_time:
        try:
            del notifications[identifier]
        except KeyError:
            pass
    else:
        notifications[identifier] = message


def log_notifications() -> None:
    """Periodically logs the current notifications every 5 seconds.

    This function runs an infinite loop, checking for the presence of notifications.
    If notifications are available, it logs them; otherwise, it logs that there are no notifications.
    """
    while True:
        time.sleep(5)
        if notifications:
            logging.info("Notifications:\n%s", json.dumps(notifications, indent=2))
        else:
            logging.info("No notifications at the moment")


def start_telemetry_with_logging() -> None:
    # Start the logger in a separate thread
    logging_thread = threading.Thread(target=log_notifications, daemon=True)
    logging_thread.start()
    # Start telemetry listening
    notifications_telemetry(_handle_notification)


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

    actions: dict[str, Callable[[], object]] = {
        "dictionary": lambda: logging.info(f"Notifications Dictionary: {dictionary()}"),
        "telemetry": start_telemetry_with_logging,
    }

    action = actions.get(args.action)
    if action:
        action()
    else:
        logging.error("Invalid action selected. Please choose a valid option.")
