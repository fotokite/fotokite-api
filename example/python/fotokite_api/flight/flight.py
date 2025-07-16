import argparse
import json
import logging
from typing import Callable, cast

import requests
from websockets.sync.client import connect

from fotokite_api.utils import BASE_REST_API_URL, BASE_WEBSOCKET_API_URL


def hard_limits() -> dict[str, object]:
    """Fetches the hard flight limits of the Kite.

    Returns:
        A dictionary containing the hard flight limits if the request is successful.
        Returns an empty dictionary if an error occurs or the request fails.

    Raises:
        requests.HTTPError: If the response status code is not 200 and an HTTP error occurs.
    """
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
    """Fetches the takeoff altitude of the Kite.

    Returns:
        A dictionary containing the takeoff altitude information if the request is successful.
        Returns an empty dictionary if an error occurs.

    Raises:
        requests.HTTPError: If the HTTP request fails with a non-200 status code.
        Exception: For any other exceptions encountered during the request.

    """
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
    """Sends a take off command to the Ground Station.

    Returns:
        True if the take off command was sent successfully (HTTP 200), False otherwise.
        This does not guarantee that the Kite will take off, only that the command was sent successfully.
        To check if the Kite has taken off, monitor the flight telemetry.
    """
    try:
        response = requests.post(f"{BASE_REST_API_URL}/commands/flight/take_off")
        if response.status_code == 200:
            logging.info("Take off command sent successfully.")
            return True
        else:
            logging.error(f"Error sending take off command: {response.text}")
    except Exception as e:
        logging.error(f"Exception in take_off: {e}")

    return False


def land() -> bool:
    """Sends a land command to the Ground Station.

    Returns:
        True if the land command was sent successfully (HTTP 200), False otherwise.
        This does not guarantee that the Kite will land, only that the command was sent successfully.
        To check if the Kite has landed, monitor the flight telemetry.
    """
    try:
        response = requests.post(f"{BASE_REST_API_URL}/commands/flight/land")
        if response.status_code == 200:
            logging.info("Land command sent successfully.")
            return True
        else:
            logging.error(f"Error sending land command: {response.text}")
    except Exception as e:
        logging.error(f"Exception in land: {e}")

    return False


def abort() -> bool:
    """Sends an abort command to the Ground Station.

    Returns:
        True if the abort command was sent successfully (HTTP 200), False otherwise.
        This command is used to stop any ongoing flight operations immediately.
        It does not guarantee that the Kite will stop immediately, but it will attempt to halt any
        ongoing flight commands.
    """
    try:
        response = requests.post(f"{BASE_REST_API_URL}/commands/flight/abort")
        if response.status_code == 200:
            logging.info("Abort command sent successfully.")
            return True
        else:
            logging.error(f"Error sending abort command: {response.text}")

    except Exception as e:
        logging.error(f"Exception in abort: {e}")

    return False


def set_altitude(altitude: float) -> bool:
    """Sends a set altitude command to the Ground Station.

    Args:
        altitude: The target altitude to set.

    Returns:
        True if the set altitude command was sent successfully (HTTP 200), False otherwise.
        This command sets the Kite's altitude to the specified value, but does not guarantee that the Kite
        will reach that altitude immediately. Monitor the flight telemetry to confirm altitude changes.
    """
    try:
        response = requests.post(
            f"{BASE_REST_API_URL}/commands/flight/set_altitude",
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


def rotate_by_angle(angle: float = 90) -> bool:
    """Sends a rotate by angle command to the Ground Station.

    Args:
        angle (float): The angle to rotate the Kite.

    Returns:
        True if the command was sent successfully, False otherwise.
        This command rotates the Kite by the specified angle. The angle should be between -360 and 360 degrees.
        Positive values indicate clockwise rotation, while negative values indicate counter-clockwise rotation.
    """
    try:
        if angle < -360 or angle > 360:
            logging.error("Angle must be between -360 and 360 degrees.")
            return False

        response = requests.post(
            f"{BASE_REST_API_URL}/commands/flight/rotate_by_angle",
            json={"angle": angle},
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
    on_message_callback: Callable[[dict[str, object]], None],
    max_messages: int | None = None,
) -> None:
    """Subscribes to flight telemetry updates from the System.

    Args:
        on_message_callback: Callback function to handle incoming telemetry messages.
        max_messages: Maximum number of messages to receive before unsubscribing. Defaults to None(read forever).
    """
    ws_url = f"{BASE_WEBSOCKET_API_URL}/telemetry/flight/subscribe"
    try:
        with connect(ws_url) as websocket:
            logging.info("Connected to flight telemetry")
            count = 0
            while True:
                message = websocket.recv()
                data = json.loads(message)
                on_message_callback(data)
                count += 1
                if max_messages is not None and count >= max_messages:
                    break
    except Exception as e:
        logging.error(f"Error in flight telemetry: {e}")


def wait_for(state: str) -> None:
    """Subscribes to telemetry updates and waits for the System to settle on a
    given state (that is, wait for a previous command to be executed).

    If this is called instantly after a command, it might falsely return because
    that command has not started executing yet.

    Args:
        state: The state to wait for (e.g. "Flying")
    """

    def check(args: dict[str, object]) -> None:
        logging.info("got telemetry update %s", args)
        if args["flight_state"] == state:
            if not args["is_changing_altitude"] and not args["is_rotating"]:
                raise StopIteration()
            else:
                logging.info("still moving...")
        else:
            logging.info("state is still %s not %s...", args["flight_state"], state)

    flight_telemetry(check)


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
            lambda data: logging.info(
                "Flight telemetry:\n%s", json.dumps(data, indent=2)
            )
        ),
        "take_off": take_off,
        "land": land,
        "abort": abort,
        "set_altitude": lambda: set_altitude(1),
        "rotate_by_angle": lambda: rotate_by_angle(90.0),
    }

    action = actions.get(args.action)
    if action:
        action()
    else:
        logging.error("Invalid action selected. Please choose a valid option.")
