import logging
from contextlib import asynccontextmanager

import pytest

from vellox import Vellox
from vellox.exceptions import LifespanFailure

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.applications import Starlette
from starlette.routing import Route


@pytest.mark.parametrize(
    "mock_flask_request, lifespan",
    [
        ({"method": "GET", "path": "/"}, "auto"),
        ({"method": "GET", "path": "/"}, "on"),
        ({"method": "GET", "path": "/"}, "off"),
    ],
    indirect=["mock_flask_request"],
)
def test_lifespan_with_asgi_app(mock_flask_request, lifespan):
    startup_complete = False
    shutdown_complete = False

    async def app(scope, receive, send):
        nonlocal startup_complete, shutdown_complete

        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                    startup_complete = True
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    shutdown_complete = True
                    return

        if scope["type"] == "http":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/json"]],
                }
            )
            await send({"type": "http.response.body", "body": b'{"Hello": "World"}'})

    handler = Vellox(app, lifespan=lifespan)
    response = handler(mock_flask_request)
    expected = lifespan in ("auto", "on")

    assert startup_complete == expected
    assert shutdown_complete == expected
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json == {"Hello": "World"}


@pytest.mark.parametrize(
    "mock_flask_request, lifespan",
    [
        ({"method": "GET", "path": "/test"}, "auto"),
        ({"method": "GET", "path": "/test"}, "on"),
        ({"method": "GET", "path": "/test"}, "off"),
    ],
    indirect=["mock_flask_request"],
)
def test_lifespan_with_fastapi(mock_flask_request, lifespan):
    startup_complete = False
    shutdown_complete = False

    @asynccontextmanager
    async def lifespan_context(app: FastAPI):
        nonlocal startup_complete
        nonlocal shutdown_complete

        startup_complete = True
        yield
        shutdown_complete = True

    app = FastAPI(lifespan=lifespan_context)

    @app.get("/")
    def root():
        return {"Hello": "World"}

    @app.get("/test")
    def test():
        return {"Hello": "Test"}

    handler = Vellox(app, lifespan=lifespan)
    response = handler(mock_flask_request)
    expected = lifespan in ("auto", "on")

    assert startup_complete == expected
    assert shutdown_complete == expected
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json == {"Hello": "Test"}


@pytest.mark.parametrize(
    "mock_flask_request, lifespan",
    [
        ({"method": "GET", "path": "/test"}, "auto"),
        ({"method": "GET", "path": "/test"}, "on"),
        ({"method": "GET", "path": "/test"}, "off"),
    ],
    indirect=["mock_flask_request"],
)
def test_lifespan_with_starlette(mock_flask_request, lifespan):
    startup_complete = False
    shutdown_complete = False

    @asynccontextmanager
    async def lifespan_context(app: Starlette):
        nonlocal startup_complete
        nonlocal shutdown_complete

        startup_complete = True
        yield
        shutdown_complete = True

    async def root(request):
        return JSONResponse({"Hello": "World"})

    async def test(request):
        return JSONResponse({"Hello": "Test"})

    app = Starlette(
        routes=[
            Route("/", root),
            Route("/test", test),
        ],
        lifespan=lifespan_context,
    )

    handler = Vellox(app, lifespan=lifespan)
    response = handler(mock_flask_request)
    expected = lifespan in ("auto", "on")

    assert startup_complete == expected
    assert shutdown_complete == expected
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json == {"Hello": "Test"}


@pytest.mark.parametrize(
    "mock_flask_request,lifespan",
    [
        ({"method": "GET", "path": "/test"}, "auto"),
        ({"method": "GET", "path": "/test"}, "on"),
    ],
    indirect=["mock_flask_request"],
)
def test_lifespan_error(mock_flask_request, lifespan, caplog) -> None:
    caplog.set_level(logging.ERROR)

    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    raise Exception("error")
        else:
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )
            await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Vellox(app, lifespan=lifespan)
    response = handler(mock_flask_request)

    assert "Exception in 'lifespan' protocol." in caplog.text
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.data == b"Hello, world!"


@pytest.mark.parametrize(
    "mock_flask_request",
    [{"method": "GET", "path": "/"}],
    indirect=True,
)
def test_lifespan_startup_failed(mock_flask_request):
    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.failed", "message": "startup failed"})

    handler = Vellox(app, lifespan="on")
    with pytest.raises(LifespanFailure):
        handler(mock_flask_request)


@pytest.mark.parametrize(
    "mock_flask_request",
    [{"method": "GET", "path": "/"}],
    indirect=True,
)
def test_lifespan_shutdown_failed(mock_flask_request):
    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send(
                        {
                            "type": "lifespan.shutdown.failed",
                            "message": "shutdown failed",
                        }
                    )
        else:
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send({"type": "http.response.body", "body": b""})

    handler = Vellox(app, lifespan="on")
    with pytest.raises(LifespanFailure):
        handler(mock_flask_request)


@pytest.mark.parametrize(
    "mock_flask_request",
    [{"method": "GET", "path": "/"}],
    indirect=True,
)
def test_lifespan_unexpected_message(mock_flask_request):
    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.unknown"})

    handler = Vellox(app, lifespan="on")
    with pytest.raises(LifespanFailure):
        handler(mock_flask_request)


@pytest.mark.parametrize(
    "mock_flask_request",
    [{"method": "GET", "path": "/"}],
    indirect=True,
)
def test_lifespan_unsupported_auto(mock_flask_request, caplog):
    caplog.set_level(logging.INFO)

    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            await send({"type": "lifespan.startup.complete"})
        else:
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send({"type": "http.response.body", "body": b""})

    handler = Vellox(app, lifespan="auto")
    response = handler(mock_flask_request)

    assert "ASGI 'lifespan' protocol appears unsupported." in caplog.text
    assert response.status_code == 200
