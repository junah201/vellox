import pytest

from vellox import Vellox
from vellox.adapter import DEFAULT_TEXT_MIME_TYPES
from vellox.exceptions import ConfigurationError


async def app(scope, receive, send): ...


def test_default_settings():
    handler = Vellox(app)

    assert handler.lifespan == "auto"
    assert handler.config["base_path"] == "/"
    assert sorted(handler.config["text_mime_types"]) == sorted(DEFAULT_TEXT_MIME_TYPES)
    assert handler.config["exclude_headers"] == []


@pytest.mark.parametrize(
    "arguments,message",
    [
        (
            {"lifespan": "unknown"},
            "Invalid argument supplied for `lifespan`. Choices are: auto|on|off",
        ),
    ],
)
def test_invalid_options(arguments, message):
    with pytest.raises(ConfigurationError) as exc:
        Vellox(app, **arguments)

    assert str(exc.value) == message
