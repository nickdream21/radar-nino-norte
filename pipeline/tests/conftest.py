from collections.abc import Iterator

import httpx
import pytest


@pytest.fixture(autouse=True)
def sin_red(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Las pruebas nunca usan la red: el transporte real falla como si no hubiera conexión."""

    def bloqueado(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("red bloqueada en las pruebas", request=request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", bloqueado)
    yield
