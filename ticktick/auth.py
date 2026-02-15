"""OAuth2 authentication for the TickTick Open API."""

import json
import os
import secrets
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests

AUTHORIZE_URL = "https://ticktick.com/oauth/authorize"
TOKEN_URL = "https://ticktick.com/oauth/token"
DEFAULT_TOKEN_PATH = Path.home() / ".ticktick_token.json"


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth callback code."""

    auth_code = None
    expected_state = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)

        if "code" in query:
            state = query.get("state", [None])[0]
            if self.expected_state and state != self.expected_state:
                self._respond(400, "State mismatch — possible CSRF. Try again.")
                return

            _OAuthCallbackHandler.auth_code = query["code"][0]
            self._respond(200, "Authorization successful! You can close this tab.")
        else:
            error = query.get("error", ["unknown"])[0]
            self._respond(400, f"Authorization failed: {error}")

    def _respond(self, status, message):
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(f"<html><body><h2>{message}</h2></body></html>".encode())

    def log_message(self, format, *args):
        pass  # Suppress request logs


def _parse_redirect_port(redirect_uri: str) -> int:
    parsed = urlparse(redirect_uri)
    return parsed.port or 8080


def authorize(client_id: str, client_secret: str, redirect_uri: str,
              token_path: Path = DEFAULT_TOKEN_PATH) -> dict:
    """Run the full OAuth2 authorization code flow.

    Opens a browser for the user to authorize, starts a local server to
    capture the callback, exchanges the code for tokens, and saves them.
    """
    state = secrets.token_urlsafe(16)
    _OAuthCallbackHandler.auth_code = None
    _OAuthCallbackHandler.expected_state = state

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "tasks:read tasks:write",
        "state": state,
    }
    auth_url = f"{AUTHORIZE_URL}?{urlencode(params)}"

    port = _parse_redirect_port(redirect_uri)
    server = HTTPServer(("127.0.0.1", port), _OAuthCallbackHandler)

    print(f"Opening browser for TickTick authorization...")
    print(f"If the browser doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for the callback (blocks until one request is handled)
    server.handle_request()
    server.server_close()

    if not _OAuthCallbackHandler.auth_code:
        raise RuntimeError("Did not receive an authorization code.")

    # Exchange code for tokens
    token_data = _exchange_code(
        client_id, client_secret, _OAuthCallbackHandler.auth_code, redirect_uri
    )

    save_token(token_data, token_path)
    print("Authorization successful. Token saved.")
    return token_data


def _exchange_code(client_id: str, client_secret: str,
                   code: str, redirect_uri: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(client_id: str, client_secret: str,
                         refresh_token: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    resp.raise_for_status()
    return resp.json()


def save_token(token_data: dict, path: Path = DEFAULT_TOKEN_PATH):
    path.write_text(json.dumps(token_data, indent=2))
    path.chmod(0o600)


def load_token(path: Path = DEFAULT_TOKEN_PATH) -> dict | None:
    if path.exists():
        return json.loads(path.read_text())
    return None
