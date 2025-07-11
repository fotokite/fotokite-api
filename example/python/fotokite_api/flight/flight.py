import argparse
import json
import logging
from typing import Callable, cast

import requests
from websockets.sync.client import connect

from fotokite_api.utils import BASE_REST_API_URL, BASE_WEBSOCKET_API_URL


def hard_limits() -> dict[str, object]:
    try:
        response = requests.get(f"{BASE_REST_API_URL}/info/flight/hard_limits")
        if response.status_code == 200:
            return cast(dict[str, object], response.json())
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching flight hard limits: {e}")

    return {}


def takeoff_altitude() -> dict[str, object]:
    try:
        response = requests.get(f"{BASE_REST_API_URL}/info/flight/takeoff_altitude")
        if response.status_code == 200:
            return cast(dict[str, object], response.json())
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching flight take off altitude: {e}")

    return {}


def take_off() -> bool:
    try:
        response = requests.post(f"{BASE_REST_API_URL}/command/flight/take_off")
        if response.status_code == 200:
            logging.info("Take off command sent successfully.")
            return True
        else:
            logging.error(f"Error sending take off command: {response.text}")
    except Exception as e:
        logging.error(f"Exception in take_off: {e}")

    return False


def land() -> bool:
    try:
        response = requests.post(f"{BASE_REST_API_URL}/command/flight/land")
        if response.status_code == 200:
            logging.info("Land command sent successfully.")
            return True
        else:
            logging.error(f"Error sending land command: {response.text}")
    except Exception as e:
        logging.error(f"Exception in land: {e}")

    return False


def abort() -> bool:
    try:
        response = requests.post(f"{BASE_REST_API_URL}/command/flight/abort")
        if response.status_code == 200:
            logging.info("Abort command sent successfully.")
            return True
        else:
            logging.error(f"Error sending abort command: {response.text}")

    except Exception as e:
        logging.error(f"Exception in abort: {e}")

    return False


def set_altitude(altitude: float) -> bool:
    try:
        response = requests.post(
            f"{BASE_REST_API_URL}/command/flight/set_altitude",
            json={"altitude": altitude},
        )
        if response.status_code == 200:
            logging.info("Set altitude command sent successfully.")
            return True
        else:
            logging.error(f"Error sending set altitude command: {response.text}")

    except Exception as e:
        logging.error(f"Exception in set_altitude: {e}")

    return False


def rotate_by_angle(angle: float) -> bool:
    try:
        if angle < -360 or angle > 360:
            logging.error("Angle must be between -360 and 360 degrees.")
            return False

        response = requests.post(
            f"{BASE_REST_API_URL}/command/flight/rotate_by_angle", json={"angle": angle}
        )
        if response.status_code == 200:
            logging.info("Rotate by angle command sent successfully.")
            return True
        else:
            logging.error(f"Error sending rotate by angle command: {response.text}")

    except Exception as e:
        logging.error(f"Exception in rotate_by_angle: {e}")

    return False


def flight_telemetry(
    on_message_callback: Callable[[dict], None], max_messages=None
) -> None:
    ws_url = f"{BASE_WEBSOCKET_API_URL}/telemetry/flight/subscribe"
    try:
        with connect(ws_url) as websocket:
            logging.info("Connected to flight telemetry")
            count = 0
            while True:
                try:
                    message = websocket.recv()
                    data = json.loads(message)
                    on_message_callback(data)
                    count += 1
                    if max_messages is not None and count >= max_messages:
                        break
                except Exception as e:
                    logging.error(f"Error receiving telemetry message: {e}")
                    break
    except Exception as e:
        logging.error(f"Error in flight telemetry: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Fotokite API Flight Example")
    parser.add_argument(
        "--action",
        choices=[
            "hard_limits",
            "takeoff_altitude",
            "telemetry",
            "take_off",
            "land",
            "abort",
            "set_altitude",
            "rotate_by_angle",
        ],
        default="hard_limits",
        help="Choose which action to trigger",
    )
    args = parser.parse_args()

    actions: dict[str, Callable[[], object]] = {
        "hard_limits": lambda: logging.info(f"Flight Hard Limits: {hard_limits()}"),
        "takeoff_altitude": lambda: logging.info(
            f"Flight Take Off Altitude: {takeoff_altitude()}"
        ),
        "telemetry": lambda: flight_telemetry(
            lambda data: logging.info(f"Telemetry message received: {data}")
        ),
        "take_off": take_off,
        "land": land,
        "abort": abort,
        "set_altitude": lambda: set_altitude(1.5),
        "rotate_by_angle": lambda: rotate_by_angle(90.0),
    }

    action = actions.get(args.action)
    if action:
        action()
    else:
        logging.error("Invalid action selected. Please choose a valid option.")
