import logging
from typing import Literal

import requests

BASE_REST_API_URL = "http://localhost:3128/api/v0"
BASE_WEBSOCKET_API_URL = "ws://localhost:3128/api/v0"


def retrieve_auth_token(
    secret: str, secret_type: Literal["key", "token"]
) -> str | None:
    try:
        if secret_type == "token":
            return secret
        else:
            response = requests.post(
                f"{BASE_REST_API_URL}/auth/token/request",
                json={"client_secret": secret},
            )
            if response.status_code == 200:
                return str(response.json().get("access_token") or "")
            else:
                response.raise_for_status()
    except Exception as e:
        logging.error(f"Error retrieving an auth token: {e}")
        return None

    return None


def retrieve_handoff(access_token: str) -> None:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(
        f"{BASE_REST_API_URL}/handoff/control/request",
        json={
            "operator_name": "API Controller",
        },
        headers=headers,
    )

    response.raise_for_status()
