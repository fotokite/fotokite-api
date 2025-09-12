import logging
import time

from fotokite_api.flight.flight import (
    land,
    rotate_by_angle,
    set_altitude,
    take_off,
    wait_for,
)
from fotokite_api.utils import API_KEY, retrieve_auth_token


def demo_sequential() -> None:
    """
    This demo sends commands and waits for them to complete, one after the
    other. The waiting uses a Websocket subscription under the hood, but this
    is hidden by an abstraction.

    Notifications are not monitored, code like this should only be used with
    Fotokite Live open in parallel.
    """

    # Retrieve an access token
    access_token = retrieve_auth_token(API_KEY)
    if access_token is None:
        logging.error("Failed to retrieve authentication token. Exiting.")
        return

    wait_for(state="StandBy")
    take_off(access_token)
    # the sleep after each command is currently required to avoid a race
    # condition where the command has *not started yet* when running the
    # `wait_for`, which would make it exit immediatly
    time.sleep(1)
    wait_for(state="Flying")
    set_altitude(2, access_token)
    time.sleep(1)
    wait_for(state="Flying")
    rotate_by_angle(access_token, 180)
    time.sleep(1)
    wait_for(state="Flying")
    rotate_by_angle(access_token, -180)
    time.sleep(1)
    wait_for(state="Flying")
    land(access_token)
    time.sleep(1)
    wait_for(state="StandBy")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_sequential()
