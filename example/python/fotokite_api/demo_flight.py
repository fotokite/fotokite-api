import logging
import threading
import time

from fotokite_api.flight.flight import (
    abort,
    flight_telemetry,
    land,
    rotate_by_angle,
    set_altitude,
    take_off,
)
from fotokite_api.notifications.notifications import notifications_telemetry
from fotokite_api.system.system import system_info, system_telemetry


def demo_flight() -> None:
    """Demonstrates a flight sequence using Fotokite API.

    This function performs the following steps:
    1. Configures logging and logs system information.
    2. Starts three telemetry threads for flight, system, and notifications, each logging received data.
    3. Initiates a takeoff sequence and logs the result.
    4. If takeoff is successful:
        - Waits for 10 seconds.
        - Sets the altitude to 1.5 meters and logs the result.
        - Waits for 3 seconds.
        - Rotates the system by 90 degrees and logs the result.
        - Waits for 5 seconds.
        - Initiates landing and logs the result.
    5. If takeoff fails, logs an error and aborts the mission.
    6. Waits to receive final telemetry messages before exiting.

    All actions and telemetry data are logged for monitoring and debugging purposes.
    """
    logging.basicConfig(level=logging.INFO)

    # Log system identity
    info = system_info()
    logging.info(f"System Info: {info}")

    # Start flight telemetry thread
    flight_thread = threading.Thread(
        target=flight_telemetry,
        args=(lambda data: logging.info(f"Flight Telemetry: {data}"),),
        kwargs={"max_messages": 20},
        daemon=True,
    )
    flight_thread.start()

    # Start system telemetry thread
    system_thread = threading.Thread(
        target=system_telemetry,
        args=(lambda data: logging.info(f"System Telemetry: {data}"),),
        kwargs={"max_messages": 20},
        daemon=True,
    )
    system_thread.start()

    # Start notifications telemetry thread
    notifications_thread = threading.Thread(
        target=notifications_telemetry,
        args=(lambda data: logging.info(f"Notifications: {data}"),),
        kwargs={"max_messages": 20},
        daemon=True,
    )
    notifications_thread.start()

    # Allow telemetry to initialize
    time.sleep(2)

    # Trigger flight commands
    if take_off():
        logging.info("Takeoff command sent.")

        time.sleep(10)

        if set_altitude(1.5):
            logging.info("Altitude set to 1.5 meters.")

        time.sleep(3)

        if rotate_by_angle(90.0):
            logging.info("Rotation by 90 degrees sent.")

        time.sleep(5)

        if rotate_by_angle(-90.0):
            logging.info("Rotation by -90 degrees sent.")

        time.sleep(5)


        if land():
            logging.info("Landing command sent.")
    else:
        logging.error("Takeoff failed. Aborting mission.")
        abort()

    # Give some time to receive final telemetry messages
    time.sleep(10)


if __name__ == "__main__":
    demo_flight()
