from __future__ import annotations

from typing import (
    List,
    Any,
    Union,
    Sequence,
    MutableMapping,
    Awaitable,
    Callable,
    Literal,
    Protocol,
    TypedDict,
)
from typing_extensions import TypeAlias

import flask


QueryParams: TypeAlias = MutableMapping[str, Union[str, Sequence[str]]]

Headers: TypeAlias = List[List[bytes]]
Message: TypeAlias = MutableMapping[str, Any]
Scope: TypeAlias = MutableMapping[str, Any]
Receive: TypeAlias = Callable[[], Awaitable[Message]]
Send: TypeAlias = Callable[[Message], Awaitable[None]]


class ASGI(Protocol):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...


LifespanMode: TypeAlias = Literal["auto", "on", "off"]


class Response(TypedDict):
    status: int
    headers: Headers
    body: bytes


class Config(TypedDict):
    base_path: str
    text_mime_types: List[str]
    exclude_headers: List[str]


class Handler(Protocol):
    def __init__(self, *args: Any) -> None: ...

    @classmethod
    def infer(cls, request: flask.Request, config: Config) -> bool: ...

    @property
    def body(self) -> bytes: ...

    @property
    def scope(self) -> Scope: ...

    def __call__(self, response: Response) -> dict: ...
