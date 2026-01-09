# Fotokite API Python Examples

## Dependency Management

We use [Poetry](https://python-poetry.org/) for dependency management and packaging.

## Makefile

To simplify running the examples, we’ve included a `Makefile` with convenient targets. You can easily run individual examples or full demo scripts using the provided commands. Please make sure you are also connected to the system's network when running these examples.

This setup helps you get up and running quickly, without having to manually manage complex commands or environments.

## Authentication

Most API endpoints require authentication. Fotokite supports two authentication methods:

- **API Key** – Used to generate authentication tokens
- **Authentication Token** – Issued either via the API or through the Tablet Token Management page (for second-party integrators)

The example scripts support both methods. Credentials can be provided either:

- As arguments to the `make` targets, or
- By setting the `secret` and `secret_type` variables directly in the `Makefile`

### Using an Authentication Token (Second party integrator)

```bash
make run_flight action="info" secret="<YOUR_TOKEN>" secret_type="token"
```

### Using an API Key (Third party integrator)

```bash
make run_flight action="info" secret="<YOUR_API_KEY>" secret_type="key"
```

### In Detail

- **System**
  All available actions can be found at `./fotokite_api/system/system.py`.
  Run: `make run_system action=<desired_action> secret=<secret> secret_type=<key || token>`

- **Flight**
  All available actions can be found at `./fotokite_api/flight/flight.py`.
  Run: `make run_flight action=<desired_action> secret=<secret> secret_type=<key || token>`

- **Notifications**
  All available actions can be found at `./fotokite_api/notifications/notifications.py`.
  Run: `make run_notifications action=<desired_action> secret=<secret> secret_type=<key || token>`

- **Flight Demo**
  Demonstrates a simple flight sequence using the Fotokite API.

  - Sets up logging for monitoring and debugging purposes.
  - Retrieves and logs system information from the Fotokite device.
  - Launches three telemetry threads to handle flight, system, and notification data streams.
  - Initiates takeoff and logs the outcome; aborts the sequence if takeoff is unsuccessful.
  - Maintains the main thread to continuously process telemetry updates until landing is detected.
  Run: `make run_demo_flight secret=<secret> secret_type=<key || token>`

- **Sequential Demo**
  This demo does the same thing as the flight demo, but with much less monitoring and error handling. This demonstrates a very simple automation based on the API that can be used while the system is still monitored via Fotokite Live.

  Run: `make run_demo_sequential secret=<secret> secret_type=<key || token>`

  ### Streamer

  The streamer package illustrates how to convert the RTSP stream to other formats. In `./streamer`, you’ll find examples using both `ffmpeg` and `gstreamer` to pipe the RTSP stream to HLS, making it accessible in a browser.

  - Run with FFMPEG (This requires ffmpeg to be installed on your system):
    `make run_ffmpeg_streamer`
  - Run with GStreamer (This requires GStreamer to be installed on your system):
    `make run_gstreamer_streamer`

<div style="background-color:#CF8008; color:white; padding:1em; border-radius:6px;">
Important <br/>
Some of these commands will start the system.<br>
Make sure the system is in an environment where it is safe to take off if a corresponding action is triggered.
</div>
<br/>
