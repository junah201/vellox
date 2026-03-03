import flask

from vellox.handlers.utils import (
    get_server_and_port,
    handle_exclude_headers,
    strip_path,
)
from vellox.types import (
    Response,
    Config,
    Scope,
)


class GCP:
    @classmethod
    def infer(cls, request: flask.Request, config: Config) -> bool:
        """Infer if this handler(GCP) can handle the request.
        Now, There are currently no other request types.
        But in the case of AWS, there are various options such as API Gateway, ALB, etc.
        This method is not only Mangum's lagacy, but also for when options are added in the future.

        Args:
            request (flask.Request): Flask request object
            config (Config): Config object
        Returns:
            bool: True if the request is a GCP request
        """
        return True

    def __init__(self, request: flask.Request, config: Config) -> None:
        self.request = request
        self.config = config

    @property
    def body(self) -> bytes:
        return self.request.get_data()

    @property
    def scope(self) -> Scope:

        return {
            "type": "http",
            "http_version": "1.1",
            "method": self.request.method,
            "headers": [
                [k.lower().encode(), v.encode()]
                for k, v in dict(self.request.headers).items()
            ],
            "path": strip_path(
                self.request.path,
                base_path=self.config["base_path"],
            ),
            "raw_path": None,
            "root_path": "",
            "scheme": self.request.scheme or "https",
            "query_string": self.request.query_string,
            "server": get_server_and_port(self.request),
            "client": (
                # TODO : Fix this
                # self.event["requestContext"].get(
                #     "identity", {}).get("sourceIp"),
                None,
                0,
            ),
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "flask.request": self.request,
        }

    def __call__(self, response: Response) -> flask.Response:
        return flask.Response(
            response=response["body"],
            status=response["status"],
            headers=handle_exclude_headers(response["headers"], self.config),
        )
