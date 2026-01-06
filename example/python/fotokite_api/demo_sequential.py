import logging
import random
import time

from fotokite_api.camera.camera import set_palette, zoom
from fotokite_api.flight.flight import (
    land,
    retrieve_handoff,
    rotate_by_angle,
    set_altitude,
    take_off,
    wait_for,
)
from fotokite_api.utils import API_KEY, retrieve_auth_token

color_palettes = [
    "BlackHot",
    "WhiteHot",
    "Ironbow",
    "Rainbow",
    "Arctic",
    "Lava",
    "Hottest",
]


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

    try:
        retrieve_handoff(access_token)
    except Exception as e:
        logging.error(f"Failed to retrieve handoff: {e}")
        return

    wait_for(access_token, state="StandBy")
    take_off(access_token)
    # the sleep after each command is currently required to avoid a race
    # condition where the command has *not started yet* when running the
    # `wait_for`, which would make it exit immediately
    wait_for(access_token, state="Flying")
    set_altitude(2, access_token)
    time.sleep(1)
    rotate_by_angle(access_token, 0, 20)
    wait_for(access_token, state="Flying")
    time.sleep(1)
    zoom(access_token, "zoom", 2.0)
    zoom(access_token, "zoom", 2.5)
    set_palette(random.choice(color_palettes))
    time.sleep(1)
    zoom(access_token, "zoom", 5.0)
    time.sleep(1)
    wait_for(access_token, state="Flying")
    rotate_by_angle(access_token, 180, 0)
    time.sleep(1)
    wait_for(access_token, state="Flying")
    rotate_by_angle(access_token, -180, 0)
    zoom(access_token, "zoom", 1)
    time.sleep(1)
    wait_for(access_token, state="Flying")
    land(access_token)
    time.sleep(1)
    wait_for(access_token, state="StandBy")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_sequential()
