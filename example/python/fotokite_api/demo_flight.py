import json
import logging
import threading
import time
from typing import Optional, TypedDict

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


class FlightState(TypedDict):
    flight_state: Optional[str]
    altitude_changed: bool
    first_rotation: bool
    second_rotation: bool
    landing: bool


state: FlightState = {
    "flight_state": None,
    "altitude_changed": False,
    "first_rotation": False,
    "second_rotation": False,
    "landing": False,
}


def handle_flight(data: dict[str, object]) -> None:
    logging.info("Flight Telemetry:\n%s", json.dumps(data, indent=2))
    flight_state = data.get("flight_state")
    if isinstance(flight_state, str):
        state["flight_state"] = flight_state

    if state["flight_state"] != "Flying":
        return

    if not state["altitude_changed"]:
        logging.info("Waiting for altitude to be set.")
        if set_altitude(1.8):
            logging.info("Altitude set to 1.8 meters.")
            state["altitude_changed"] = True

    elif state["altitude_changed"] and not state["first_rotation"]:
        logging.info("Waiting for first rotation to complete.")
        if rotate_by_angle(180.0):
            logging.info("Rotation by 180 degrees sent.")
            state["first_rotation"] = True

    elif (
        state["altitude_changed"]
        and state["first_rotation"]
        and not state["second_rotation"]
    ):
        logging.info("Waiting for second rotation to complete.")
        if rotate_by_angle(-90.0):
            logging.info("Rotation by -90 degrees sent.")
            state["second_rotation"] = True

    elif (
        state["altitude_changed"]
        and state["first_rotation"]
        and state["second_rotation"]
        and not state["landing"]
    ):
        logging.info("All actions completed, preparing to land.")
        if land():
            logging.info("Landing command sent.")
            state["landing"] = True


def demo_flight() -> None:
    """Demonstrates a flight sequence using Fotokite API.

    1. Configures logging for monitoring and debugging.
    2. Fetches and logs system information.
    3. Starts three telemetry threads for flight, system, and notifications, each logging received data.
    4. Initiates takeoff and logs the result; aborts if takeoff fails.
    5. Keeps the main thread alive to process telemetry updates until landing is detected.
    6. Performs different flight commands (altitude change, rotations etc.) in response to telemetry data.
    7. Waits briefly after landing to capture final telemetry data.

    All actions and telemetry data are logged for monitoring and debugging purposes.
    """
    logging.basicConfig(level=logging.INFO)

    # Identify the system
    info = system_info()
    logging.info("System Info:\n%s", json.dumps(info, indent=2))

    # Start telemetry threads
    flight_thread = threading.Thread(
        target=flight_telemetry,
        args=(handle_flight,),
        daemon=True,
    )
    flight_thread.start()

    system_thread = threading.Thread(
        target=system_telemetry,
        args=(
            lambda data: logging.info(
                "System Telemetry:\n%s", json.dumps(data, indent=2)
            ),
        ),
        daemon=True,
    )
    system_thread.start()

    notifications_thread = threading.Thread(
        target=start_telemetry_with_logging,
        daemon=True,
    )
    notifications_thread.start()

    # Allow telemetry to start
    time.sleep(2)

    if take_off():
        logging.info("Takeoff command sent.")
    else:
        logging.error("Takeoff failed. Aborting mission.")
        abort()
        return

    # Keep the main thread alive to process telemetry updates
    while not state["landing"]:
        time.sleep(1)

    # Allow time for final telemetry after landing
    time.sleep(10)


if __name__ == "__main__":
    demo_flight()
