import argparse
import json
import logging
from typing import Callable, cast

import requests
from websockets.sync.client import connect

from fotokite_api.utils import (
    API_KEY,
    BASE_REST_API_URL,
    BASE_WEBSOCKET_API_URL,
    retrieve_auth_token,
)


def info(access_token: str) -> dict[str, object]:
    """Fetches the hard flight limits of the Kite.

    Args:
        access_token: The authentication token to use in the request.

    Returns:
        A dictionary containing the hard flight limits if the request is successful.
        Returns an empty dictionary if an error occurs or the request fails.

    Raises:
        requests.HTTPError: If the response status code is not 200 and an HTTP error occurs.
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{BASE_REST_API_URL}/flight/info", headers=headers)
        if response.status_code == 200:
            return cast(dict[str, object], response.json())
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching flight hard limits: {e}")

    return {}


def take_off(access_token: str) -> bool:
    """Sends a take off command to the Ground Station.

    Args:
        access_token: The authentication token to use in the request.

    Returns:
        True if the take off command was sent successfully (HTTP 200), False otherwise.
        This does not guarantee that the Kite will take off, only that the command was sent successfully.
        To check if the Kite has taken off, monitor the flight telemetry.
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(
            f"{BASE_REST_API_URL}/flight/control/take_off", headers=headers
        )
        if response.status_code == 200:
            logging.info("Take off command sent successfully.")
            return True
        else:
            logging.error(f"Error sending take off command: {response.text}")
    except Exception as e:
        logging.error(f"Exception in take_off: {e}")

    return False


def land(access_token: str) -> bool:
    """Sends a land command to the Ground Station.

    Args:
        access_token: The authentication token to use in the request.

    Returns:
        True if the land command was sent successfully (HTTP 200), False otherwise.
        This does not guarantee that the Kite will land, only that the command was sent successfully.
        To check if the Kite has landed, monitor the flight telemetry.
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(
            f"{BASE_REST_API_URL}/flight/control/land", headers=headers
        )
        if response.status_code == 200:
            logging.info("Land command sent successfully.")
            return True
        else:
            logging.error(f"Error sending land command: {response.text}")
    except Exception as e:
        logging.error(f"Exception in land: {e}")

    return False


def abort(access_token: str) -> bool:
    """Sends an abort command to the Ground Station.

    Args:
        access_token: The authentication token to use in the request.

    Returns:
        True if the abort command was sent successfully (HTTP 200), False otherwise.
        This command is used to stop any ongoing flight operations immediately.
        It does not guarantee that the Kite will stop immediately, but it will attempt to halt any
        ongoing flight commands.
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(
            f"{BASE_REST_API_URL}/flight/control/abort", headers=headers
        )
        if response.status_code == 200:
            logging.info("Abort command sent successfully.")
            return True
        else:
            logging.error(f"Error sending abort command: {response.text}")

    except Exception as e:
        logging.error(f"Exception in abort: {e}")

    return False


def set_altitude(altitude: float, access_token: str) -> bool:
    """Sends a set altitude command to the Ground Station.

    Args:
        altitude: The target altitude to set.
        access_token: The authentication token to use in the request.

    Returns:
        True if the set altitude command was sent successfully (HTTP 200), False otherwise.
        This command sets the Kite's altitude to the specified value, but does not guarantee that the Kite
        will reach that altitude immediately. Monitor the flight telemetry to confirm altitude changes.
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(
            f"{BASE_REST_API_URL}/flight/control/altitude",
            json={"altitude": altitude},
            headers=headers,
        )
        if response.status_code == 200:
            logging.info("Set altitude command sent successfully.")
            return True
        else:
            logging.error(f"Error sending set altitude command: {response.text}")

    except Exception as e:
        logging.error(f"Exception in set_altitude: {e}")

    return False


def rotate_by_angle(access_token: str, pan: float = 0.0, tilt: float = 0.0) -> bool:
    """Sends a rotate by angle command to the Ground Station.

    Args:
        pan: The pan angle to rotate the Kite's camera.
        tilt: The tilt angle to rotate the Kite's camera.
        access_token: The authentication token to use in the request.

    Returns:
        True if the command was sent successfully, False otherwise.
        This command rotates the Kite's camera by the specified pan and tilt angles.
        Pan and tilt should be between -180 and 180 degrees.
        Positive values indicate clockwise/upward rotation, negative values indicate counter-clockwise/downward.
    """
    try:
        if not (-180 <= pan <= 180) or not (-180 <= tilt <= 180):
            logging.error("Pan and tilt must be between -180 and 180 degrees.")
            return False

        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(
            f"{BASE_REST_API_URL}/camera/control/rotate_by_angle",
            json={
                "pan": pan,
                "tilt": tilt,
            },
            headers=headers,
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
    access_token: str = "",
    max_messages: int | None = None,
) -> None:
    """Subscribes to flight telemetry updates from the System.

    Args:
        on_message_callback: Callback function to handle incoming telemetry messages.
        access_token: The authentication token to use in the websocket connection.
        max_messages: Maximum number of messages to receive before unsubscribing. Defaults to None(read forever).
    """
    ws_url = f"{BASE_WEBSOCKET_API_URL}/flight/state/subscribe"
    try:
        with connect(
            ws_url, additional_headers={"Authorization": f"Bearer {access_token}"}
        ) as websocket:
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


def wait_for(access_token: str, state: str) -> None:
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

    flight_telemetry(check, access_token)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Fotokite API Flight Example")
    parser.add_argument(
        "--action",
        choices=[
            "info",
            "telemetry",
            "take_off",
            "land",
            "abort",
            "set_altitude",
            "rotate_by_angle",
        ],
        default="info",
        help="Choose which action to trigger",
    )
    args = parser.parse_args()

    access_token = retrieve_auth_token(API_KEY)
    if not access_token:
        logging.error("Failed to retrieve access token. Exiting.")
        exit(1)

    actions: dict[str, Callable[[str], object]] = {
        "info": lambda access_token: logging.info(f"Flight Info: {info(access_token)}"),
        "telemetry": lambda access_token: flight_telemetry(
            lambda data: logging.info(
                "Flight telemetry:\n%s", json.dumps(data, indent=2)
            ),
            access_token=access_token,
        ),
        "take_off": take_off,
        "land": land,
        "abort": abort,
        "set_altitude": lambda access_token: set_altitude(1, access_token),
        "rotate_by_angle": lambda access_token: rotate_by_angle(access_token, 90.0),
    }

    action = actions.get(args.action)
    if action:
        action(access_token)
    else:
        logging.error("Invalid action selected. Please choose a valid option.")
