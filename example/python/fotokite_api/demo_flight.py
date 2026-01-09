import argparse
import json
import logging
import threading
import time
from typing import Literal, TypedDict

from fotokite_api.flight.flight import (
    abort,
    flight_telemetry,
    land,
    rotate_by_angle,
    set_altitude,
    take_off,
)
from fotokite_api.notifications.notifications import start_telemetry_with_logging
from fotokite_api.system.system import system_info, system_telemetry
from fotokite_api.utils import retrieve_auth_token, retrieve_handoff


class FlightState(TypedDict):
    altitude_changed: bool
    first_rotation: bool
    second_rotation: bool
    landing: bool


state: FlightState = {
    "altitude_changed": False,
    "first_rotation": False,
    "second_rotation": False,
    "landing": False,
}


def demo_flight(secret: str, secret_type: Literal["key", "token"]) -> None:
    """Demonstrates a flight sequence using the Fotokite API.

    This function performs the following steps:
        1. Configures logging for informational output.
        2. Retrieves and logs system information (Identity, components etc...).
        3. Starts telemetry threads for flight, system, and notifications.
        4. Sends a takeoff command and logs the result.
        6. Performs a sequence of maneuvers:
        - Sets altitude to 2 meters.
        - Rotates by 180 degrees.
        - Rotates back by -180 degrees.
        - Lands the Fotokite.
        5. If takeoff fails, aborts the mission and exits.
        6. Keeps the main thread alive, monitoring for landing state.
        7. After landing, waits to collect final telemetry data.
    """
    logging.basicConfig(level=logging.INFO)

    # Retrieve an access token
    access_token = retrieve_auth_token(secret, secret_type)
    if access_token is None:
        logging.error("Failed to retrieve authentication token. Exiting.")
        return

    try:
        retrieve_handoff(access_token)
    except Exception as e:
        logging.error(f"Failed to retrieve handoff: {e}")
        return

    # Identify the system
    info = system_info(access_token)
    logging.info("System Info:\n%s", json.dumps(info, indent=2))

    # Start telemetry threads
    flight_thread = threading.Thread(
        target=flight_telemetry,
        args=(handle_flight, access_token),
        daemon=True,
    )
    flight_thread.start()

    system_thread = threading.Thread(
        target=system_telemetry,
        args=(
            lambda data: logging.info(
                "System Telemetry:\n%s", json.dumps(data, indent=2)
            ),
            access_token,
        ),
        daemon=True,
    )
    system_thread.start()

    notifications_thread = threading.Thread(
        target=start_telemetry_with_logging,
        args=(access_token,),
        daemon=True,
    )
    notifications_thread.start()

    # Allow telemetry to start
    time.sleep(2)

    if take_off(access_token):
        logging.info("Takeoff command sent.")
    else:
        logging.error("Takeoff failed. Aborting mission.")
        abort(access_token)
        return

    # Keep the main thread alive to process telemetry updates
    while not state["landing"]:
        time.sleep(1)

    # Final wait after landing to collect telemetry
    time.sleep(10)


def handle_flight(data: dict[str, object], access_token: str) -> None:
    """Handles flight telemetry data and executes flight commands based on the current flight state."""

    logging.info("Flight Telemetry:\n%s", json.dumps(data, indent=2))

    flight_state = data.get("flight_state", "Unknown")
    is_changing_altitude = data.get("is_changing_altitude", False)
    is_rotating = data.get("is_rotating", False)

    if flight_state != "Flying":
        return

    if not state["altitude_changed"]:
        logging.info("Setting altitude to 2 meters.")
        if set_altitude(2, access_token):
            logging.info("Altitude set command sent.")
            state["altitude_changed"] = True

    elif not state["first_rotation"] and not is_changing_altitude:
        logging.info("Rotating by 180 degrees.")
        if rotate_by_angle(access_token, 180, 0):
            logging.info("Rotation command (180 deg) sent.")
            state["first_rotation"] = True

    elif not state["second_rotation"] and not is_rotating and not is_changing_altitude:
        logging.info("Rotating back by -180 degrees.")
        if rotate_by_angle(access_token, -180, 0):
            logging.info("Rotation command (-180 deg) sent.")
            state["second_rotation"] = True

    elif not state["landing"] and not is_rotating and not is_changing_altitude:
        logging.info("Landing now.")
        if land(access_token):
            logging.info("Landing command sent.")
            state["landing"] = True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fotokite API Camera Example")
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

    demo_flight(args.secret, args.secret_type)
