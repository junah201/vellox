import logging
from itertools import chain
from contextlib import ExitStack
from typing import List, Optional, Type

import flask

from vellox.protocols import HTTPCycle, LifespanCycle
from vellox.handlers import GCP
from vellox.exceptions import ConfigurationError
from vellox.types import (
    ASGI,
    LifespanMode,
    Config,
    Handler,
)


logger = logging.getLogger("vellox")


HANDLERS: List[Type[Handler]] = [GCP]

DEFAULT_TEXT_MIME_TYPES: List[str] = [
    "text/",
    "application/json",
    "application/javascript",
    "application/xml",
    "application/vnd.api+json",
    "application/vnd.oai.openapi",
]


class Vellox:
    def __init__(
        self,
        app: ASGI,
        lifespan: LifespanMode = "auto",
        base_path: str = "/",
        custom_handlers: Optional[List[Type[Handler]]] = None,
        text_mime_types: Optional[List[str]] = None,
        exclude_headers: Optional[List[str]] = None,
    ) -> None:
        if lifespan not in ("auto", "on", "off"):
            raise ConfigurationError(
                "Invalid argument supplied for `lifespan`. Choices are: auto|on|off"
            )

        self.app = app
        self.lifespan = lifespan
        self.custom_handlers = custom_handlers or []
        exclude_headers = exclude_headers or []
        self.config = Config(
            base_path=base_path or "/",
            text_mime_types=text_mime_types or [*DEFAULT_TEXT_MIME_TYPES],
            exclude_headers=[header.lower() for header in exclude_headers],
        )

    def infer(self, request: flask.Request) -> Handler:
        for handler_cls in chain(self.custom_handlers, HANDLERS):
            if handler_cls.infer(request, self.config):
                return handler_cls(request, self.config)
        raise RuntimeError(
            "The adapter was unable to infer a handler to use for the event. This "
            "is likely related to how the GCP Cloud Functions was invoked. (Are you "
            "testing locally? Make sure the request payload is valid for a "
            "supported handler.)"
        )  # pragma: no cover

    def handler(self, request: flask.Request) -> flask.Response:
        return self.__call__(request)

    def __call__(self, request: flask.Request) -> flask.Response:
        handler = self.infer(request)
        with ExitStack() as stack:
            if self.lifespan in ("auto", "on"):
                lifespan_cycle = LifespanCycle(self.app, self.lifespan)
                stack.enter_context(lifespan_cycle)

            http_cycle = HTTPCycle(handler.scope, handler.body)
            http_response = http_cycle(self.app)

            return handler(http_response)

        assert False, "unreachable"  # pragma: no cover
