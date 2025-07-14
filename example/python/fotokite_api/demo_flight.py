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
        logging.info("Setting altitude to 1 meter.")
        if set_altitude(1):
            logging.info("Altitude set command sent.")
            time.sleep(5)
            state["altitude_changed"] = True

    elif not state["first_rotation"]:
        logging.info("Rotating by 180 degrees.")
        if rotate_by_angle(180.0):
            logging.info("Rotation command (180 deg) sent.")
            time.sleep(15)
            state["first_rotation"] = True

    elif not state["second_rotation"]:
        logging.info("Rotating back by -180 degrees.")
        if rotate_by_angle(-180.0):
            logging.info("Rotation command (-180 deg) sent.")
            time.sleep(15)
            state["second_rotation"] = True

    elif not state["landing"]:
        logging.info("Landing now.")
        if land():
            logging.info("Landing command sent.")
            time.sleep(15)
            state["landing"] = True


def demo_flight() -> None:
    """Demonstrates a flight sequence using Fotokite API with waits after each command."""
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


if __name__ == "__main__":
    demo_flight()
