from typing import Any, Dict, List, Tuple
from urllib.parse import unquote

import flask

from vellox.types import Config


def get_server_and_port(request: flask.Request) -> Tuple[str, int]:
    server_name = request.headers.get("host", "vellox")
    server_port = 80
    server = (server_name, int(server_port))

    return server


def strip_path(path: str, *, base_path: str) -> str:
    if not path:
        return "/"

    if base_path and base_path != "/":
        if not base_path.startswith("/"):
            base_path = f"/{base_path}"
        if path.startswith(base_path):
            path = path[len(base_path) :]

    return unquote(path)


def handle_exclude_headers(
    headers: List[Tuple[bytes, bytes]], config: Config
) -> Dict[str, Any]:
    finalized_headers = {}
    for h in headers:
        header_key, header_value = h
        header_key = header_key.decode()
        header_value = header_value.decode()
        if header_key in config["exclude_headers"]:
            continue
        finalized_headers[header_key] = header_value

    return finalized_headers
