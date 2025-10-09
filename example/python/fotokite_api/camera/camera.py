import argparse
import json
import logging
import threading
import time
from typing import Callable, cast

import requests
from websockets.sync.client import connect

from fotokite_api.utils import (
    API_KEY,
    BASE_REST_API_URL,
    BASE_WEBSOCKET_API_URL,
    retrieve_auth_token,
)

VideoStreamMessage = dict[str, object]
VideoStream = dict[str, str]
video_streams: dict[str, VideoStream] = {}


def list_videostreams(access_token: str = "") -> VideoStreamMessage:
    """Fetches the list of available video streams.

    Args:
        access_token: Bearer token for API authentication. Defaults to "".

    Returns:
        Parsed JSON response containing video stream information if successful.
        An empty dictionary if an error occurs.

    Raises:
        requests.HTTPError: If the response status code is not 200.
        Exception: For any other errors during the request.
    """
    try:
        response: requests.Response = requests.get(
            f"{BASE_REST_API_URL}/videostreams",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 200:
            return cast(VideoStreamMessage, response.json())
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error fetching video stream info: {e}")

    return {}


def zoom(
    access_token: str = "", stream_id: str = "zoom", zoom_level: float = 1.0
) -> bool:
    """Adjusts the zoom level of a specified video stream.

    Args:
        access_token: Bearer token for API authentication.
        stream_id: Identifier of the video stream to zoom. Defaults to "zoom".
        zoom_level: Desired zoom level. Defaults to 1.0.

    Returns:
        True if the zoom level was successfully changed, False otherwise.

    Raises:
        requests.HTTPError: If the API request fails with a non-200 status code.
    """
    try:
        response: requests.Response = requests.post(
            f"{BASE_REST_API_URL}/videostreams/{stream_id}/control/zoom",
            json={"zoom_level": zoom_level},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 200:
            logging.info("Zoom level changed to %s", zoom_level)
            return True
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error changing zoom level: {e}")

    return False


def set_palette(
    access_token: str = "", stream_id: str = "thermal", palette: str = "Rainbow"
) -> bool:
    """Sets the thermal color palette for a specified video stream.

    Args:
        access_token: The access token for authentication. Defaults to an empty string.
        stream_id: The ID of the video stream to modify. Defaults to "thermal".
        palette: The name of the thermal color palette to set. Defaults to "Rainbow".

    Returns:
        True if the palette was successfully changed, False otherwise.

    Raises:
        requests.HTTPError: If the HTTP request fails with a non-200 status code.
    """
    try:
        response: requests.Response = requests.post(
            f"{BASE_REST_API_URL}/videostreams/{stream_id}/control/palette",
            json={"thermal_color_palette": palette},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 200:
            logging.info("Palette changed to %s", palette)
            return True
        else:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error changing zoom level: {e}")

    return False


def videostreams_telemetry(
    on_message_callback: Callable[[list[VideoStream]], None],
    access_token: str,
    stream_id: str = "",
    max_messages: int | None = None,
) -> None:
    if stream_id == "":
        logging.error(f"No stream id provided")
        return

    ws_url = f"{BASE_WEBSOCKET_API_URL}/videostreams/{stream_id}/state/subscribe"

    logging.info(ws_url)

    try:
        with connect(
            ws_url, additional_headers={"Authorization": f"Bearer {access_token}"}
        ) as websocket:
            logging.info("Connected to video streams telemetry")
            count = 0
            while True:
                message = websocket.recv()
                data = json.loads(message)
                on_message_callback(data)

                count += 1
                if max_messages is not None and count >= max_messages:
                    break
    except Exception as e:
        logging.error(f"Error in camera telemetry: {e}")


def _handle_videostreams(messages: list[VideoStream]) -> None:
    """Processes a video stream message, updating the global video streams store."""
    for message in messages:
        identifier = f"{message.get('id')}"

        video_streams[identifier] = message


def log_videostreams() -> None:
    """Periodically logs the current camera telemetry every 5 seconds."""
    while True:
        time.sleep(5)
        if video_streams:
            logging.info("Video Streams:\n%s", json.dumps(video_streams, indent=2))
        else:
            logging.info("No video streams at the moment")


def start_telemetry_with_logging(
    access_token: str, stream_id: str | None = None
) -> None:
    # Start the logger in a separate thread
    logging_thread = threading.Thread(target=log_videostreams, daemon=True)
    logging_thread.start()
    # Start telemetry listening
    videostreams_telemetry(_handle_videostreams, access_token, stream_id=stream_id)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Fotokite API Camera Example")
    parser.add_argument(
        "--action",
        choices=["zoom", "palette", "list", "telemetry", "telemetry_all"],
        default="list",
        help="Choose which action to trigger",
    )
    args = parser.parse_args()

    actions: dict[str, Callable[[str], object]] = {
        "list": lambda access_token: logging.info(list_videostreams(access_token)),
        "telemetry": start_telemetry_with_logging,
        "zoom": lambda access_token: zoom(access_token, "zoom", zoom_level=4.0),
        "palette": lambda access_token: set_palette(
            access_token, "thermal", palette="Rainbow"
        ),
    }

    auth_token = retrieve_auth_token(API_KEY)
    if auth_token is None:
        logging.error("Failed to retrieve authentication token. Exiting.")
        exit(1)

    action = actions.get(args.action)
    if action:
        action(auth_token)
    else:
        logging.error("Invalid action selected. Please choose a valid option.")
