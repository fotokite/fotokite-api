import argparse
import json
import logging
import threading
import time

import requests
from websockets.sync.client import connect

from fotokite_api.utils import BASE_REST_API_URL, BASE_WEBSOCKET_API_URL

notifications = {}


def dictionary() -> dict:
    try:
        response = requests.get(f"{BASE_REST_API_URL}/info/notifications/dictionary")
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching notifications dictionary: {e}")
        return {}


def notifications_telemetry(
    on_message_callback, max_messages=None, from_time=None
) -> None:
    if from_time is None:
        now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() - 600))
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


def _handle_notifications(message: list[dict]):
    for notification in message.get("notifications", []):
        identifier = f"{notification.get("code")}_{notification.get("begin_time")}"
        end_time = notification.get("end_time")

        if end_time:
            try:
                del notifications[identifier]
            except KeyError:
                pass
        else:
            notifications[identifier] = notification


def log_notifications():
    while True:
        time.sleep(5)
        if notifications:
            logging.info(f"Current notifications: {notifications}")
        else:
            logging.info("No notifications at the moment")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Fotokite API Notifications Example")
    parser.add_argument(
        "--action",
        choices=["dictionary", "telemetry"],
        default="dictionary",
        help="Choose which action to trigger",
    )
    args = parser.parse_args()

    def start_telemetry_with_logging():
        # Start logging notifications in a separate thread
        logging_thread = threading.Thread(target=log_notifications, daemon=True)
        logging_thread.start()
        # Start telemetry listening
        notifications_telemetry(_handle_notifications)

    actions = {
        "dictionary": lambda: logging.info(f"Notifications Dictionary: {dictionary()}"),
        "telemetry": start_telemetry_with_logging,
    }

    action = actions.get(args.action)
    if action:
        action()
    else:
        logging.error("Invalid action selected. Please choose a valid option.")
