import http.server
import logging
import os
import signal
import socketserver
import subprocess
import sys
import threading
from typing import Any, List, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

""" CORS support for browsers to access HLS streams """


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers", "Range, Content-Type, Origin, Accept"
        )
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(200, "ok")
        self.end_headers()


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def start_gstreamer(rtsp_url: str, hls_dir: str) -> subprocess.Popen[bytes]:
    """Starts a GStreamer pipeline to stream RTSP video and convert it to HLS segments.

    Args:
        rtsp_url: The RTSP URL of the video stream source.
        hls_dir: The directory where HLS segments and playlist will be stored.

    Returns:
        The process running the GStreamer pipeline.
    """
    playlist_path: str = os.path.join(hls_dir, "playlist.m3u8")

    if not os.path.exists(hls_dir):
        os.makedirs(hls_dir)

    cmd: List[str] = [
        "gst-launch-1.0",
        "rtspsrc",
        f"location={rtsp_url}",
        "latency=0",
        "!",
        "rtph264depay",
        "!",
        "h264parse",
        "!",
        "mpegtsmux",
        "!",
        "hlssink",
        f"location={hls_dir}/segment%05d.ts",
        f"playlist-location={playlist_path}",
        "target-duration=2",
        "max-files=5",
    ]

    process = subprocess.Popen(
        cmd, stdout=sys.stdout, stderr=sys.stderr, start_new_session=True
    )
    logging.info(f"Started GStreamer for {rtsp_url}")
    return process


def start_http_server(
    hls_dir: str, port: int
) -> Tuple[threading.Thread, socketserver.TCPServer]:
    """Starts an HTTP server to serve files from the specified HLS directory with CORS support.

    Args:
        hls_dir: Path to the directory containing HLS files to be served.
        por: Port number on which the HTTP server will listen.

    Returns:
        A tuple containing the thread running the server and the server instance itself.
    """
    os.chdir(hls_dir)

    httpd: ReusableTCPServer = ReusableTCPServer(("", port), CORSRequestHandler)

    def serve() -> None:
        logging.info(f"Serving HLS on http://localhost:{port}/playlist.m3u8")
        try:
            httpd.serve_forever()
        except Exception as e:
            logging.error(f"HTTP server error: {e}")

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return thread, httpd


def main() -> None:
    """Starts GStreamer processes and HTTP servers for multiple RTSP streams, manages their lifecycles, and handles graceful shutdown on SIGINT or SIGTERM.

    The function:
    - Configures multiple RTSP streams and corresponding HLS output directories and HTTP ports.
    - Launches GStreamer processes to convert RTSP streams to HLS.
    - Starts HTTP servers to serve the HLS streams.
    - Registers signal handlers to gracefully terminate all processes and servers on shutdown signals.
    - Waits for all server threads to finish before exiting.

    """

    # Mapping of RTSP streams to HLS directories and ports
    configs: List[Tuple[str, str, str, int]] = [
        ("Thermal", "rtsp://192.168.2.100:5012/video", "/tmp/hlsThermal", 8082),
        ("Color", "rtsp://192.168.2.100:5010/video", "/tmp/hlsColor", 8083),
    ]

    processes: List[subprocess.Popen[bytes]] = []
    servers: List[socketserver.TCPServer] = []
    threads: List[threading.Thread] = []

    # Start GStreamer processes and HTTP servers for each RTSP stream
    for _, rtsp_url, hls_dir, port in configs:
        proc = start_gstreamer(rtsp_url, hls_dir)
        thread, httpd = start_http_server(hls_dir, port)
        processes.append(proc)
        servers.append(httpd)
        threads.append(thread)

    # Handle graceful shutdown on SIGINT or SIGTERM
    def shutdown(signum: int, frame: Any) -> None:
        logging.info("Received shutdown signal, stopping everything...")

        # Stop GStreamer processes
        for proc in processes:
            try:
                pgid: int = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL)
                logging.info(f"Stopped GStreamer process group {pgid}")
            except Exception as e:
                logging.error(f"Error stopping GStreamer process: {e}")

        # Stop HTTP servers
        for httpd in servers:
            try:
                httpd.shutdown()
                logging.info("HTTP server shut down")
            except Exception as e:
                logging.error(f"Error shutting down server: {e}")

        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for threads to finish (they will stop after shutdown)
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        shutdown(signal.SIGINT, None)


if __name__ == "__main__":
    main()
