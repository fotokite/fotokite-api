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


def demo_flight() -> None:
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

    # Final wait after landing to collect telemetry
    time.sleep(10)


def handle_flight(data: dict[str, object]) -> None:
    """Handles flight telemetry data and executes flight commands based on the current flight state."""

    logging.info("Flight Telemetry:\n%s", json.dumps(data, indent=2))

    flight_state = data.get("flight_state", "Unknown")
    is_changing_altitude = data.get("is_changing_altitude", False)
    is_rotating = data.get("is_rotating", False)

    if flight_state != "Flying":
        return

    if not state["altitude_changed"]:
        logging.info("Setting altitude to 2 meters.")
        if set_altitude(2):
            logging.info("Altitude set command sent.")
            state["altitude_changed"] = True

    elif not state["first_rotation"] and not is_changing_altitude:
        logging.info("Rotating by 180 degrees.")
        if rotate_by_angle(180.0):
            logging.info("Rotation command (180 deg) sent.")
            state["first_rotation"] = True

    elif not state["second_rotation"] and not is_rotating and not is_changing_altitude:
        logging.info("Rotating back by -180 degrees.")
        if rotate_by_angle(-180.0):
            logging.info("Rotation command (-180 deg) sent.")
            state["second_rotation"] = True

    elif not state["landing"] and not is_rotating and not is_changing_altitude:
        logging.info("Landing now.")
        if land():
            logging.info("Landing command sent.")
            state["landing"] = True


if __name__ == "__main__":
    demo_flight()
