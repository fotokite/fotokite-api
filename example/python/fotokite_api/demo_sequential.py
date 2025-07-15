import logging
import time

from fotokite_api.flight.flight import (
    land,
    rotate_by_angle,
    set_altitude,
    take_off,
    wait_for,
)


def demo_sequential() -> None:
    wait_for(state="StandBy")
    take_off()
    time.sleep(1)
    wait_for(state="Flying")
    set_altitude(2)
    time.sleep(1)
    wait_for(state="Flying")
    rotate_by_angle(180)
    time.sleep(1)
    wait_for(state="Flying")
    rotate_by_angle(-180)
    time.sleep(1)
    wait_for(state="Flying")
    land()
    time.sleep(1)
    wait_for(state="StandBy")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_sequential()
