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

## TLS and Secure Connectivity

The Fotokite system uses TLS (Transport Layer Security) to encrypt data between your application and the Ground Station (GS). When operating on the local network, there are two primary ways to establish a secure connection.

The Ground Station typically listens for secure traffic on port **8443**.

### Hostname-Based Verification (Standard TLS)

This method treats the Ground Station like a standard website. The URL format is `https://<GS_NAME>.sigma.fotokite-test.com:8443`.

***Setup:** You must map the Ground Station's local IP to its hostname in your local `hosts` file (e.g., `/etc/hosts` on Ubuntu):
`192.168.2.100  g028b.sigma.fotokite.com`
***Internet Requirement:** The system uses CertMagic to manage certificates via the Google Public CA. The Ground Station **must connect to the internet at least once every 90 days** to renew its certificate.
***Failure Case:** If the certificate expires while the system is offline, standard TLS verification will fail, and the API will become inaccessible via this method until an internet connection is restored and the certificate is auto-renewed.

### Public Key Pinning (Offline Resilient)

For field operations where internet access is unreliable, we recommend **Public Key Pinning**. This method allows you to connect via the local IP address (e.g., `https://192.168.2.100:8443`) and ignore the certificate expiration date while still maintaining security.

Instead of trusting a Certificate Authority (CA), your application trusts a specific cryptographic hash of the Ground Station's Public Key.

**Resilience:** Works indefinitely without an internet connection. Even if the certificate technically "expires," the connection remains secure because the Public Key hasn't changed.
**Retrieving the Pin-Hash:** You can retrieve the SHA-256 pin-hash of your Ground Station by running the following command (Ubuntu):

```bash
echo | openssl s_client -connect <GS_IP>:8443 2>/dev/null | openssl x509 -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | openssl enc -base64

```

***Usage:** Pass the resulting hash to the `--public_key` argument in the example scripts.

### Examples

Detailed implementation of both methods can be found in `./tls/`.

***Run via Hostname:**
`make run_tls_example action=hostname hostname=g1538zh secret=<secret> secret_type=<key || token>`
***Run via Pinned Key:**
`make run_tls_example action=pinned_key public_key="<YOUR_HASH>" secret=<secret> secret_type=<key || token>`

### Tests

You can run some containerized tests with time spooming that simulate certificate expiration, so you get a better feel of what to expect.

Prerequisites:

- Docker installed.
- Connection to the GS network.
- Valid API token and public key.

#### **What these tests prove:**

**Hostname Mode:** Will fail in the "future" because standard security requires an internet update every 30 days.
**Pinned Key Mode:** Will stay working forever, even years into the future without internet.

#### **How to run them:**

1. **Configure the Makefile:**

Fill in your Ground Station's details:

```makefile
gs_ip = 192.168.2.100
gs_name = G2505ZH
secret = <YOUR_TOKEN>
public_key = <YOUR_PUBLIC_KEY_HASH>

```

2. **Execute the Time Travel tests:**

```bash
make test_tls

# You can also skip step 1 and just pass in the variables as params directly
make test_tls gs_name="g2211ZR" secret="zp2319UQO543NtE8tVvya19en_4RofaX1-h8nvE_YCUwfuN_eMuljSSwFsGH6mFQvTI=" secret_type="token" public_key="TXGEHuBaJE31UETqrgHYCLD2Fg2Kn2LV2fv2642v6/I="
```

#### **What to look for in the results:**

| Test Action | Clock Set To | Result | Why? |
| --- | --- | --- | --- |
| `hostname` | **Today** | PASS | Everything is valid. |
| `hostname` | **-2 Years** | FAIL | The certificate is not valid yet. |
| `hostname` | **+2 Years** | FAIL | The certificate expired. |
| `pinned_key` | **Today** | PASS | The key matches. |
| `pinned_key` | **-2 Years** | PASS | The key matches. |
| `pinned_key` | **+2 Years** | PASS | Success, pinning ignores
| `wrong pinned_key` | **Today** | FAIL | The public key is invalid the date. |

<div style="background-color:#CF8008; color:white; padding:1em; border-radius:6px;">
Important <br/>
Some of these commands will start the system.<br>
Make sure the system is in an environment where it is safe to take off if a corresponding action is triggered.
</div>
