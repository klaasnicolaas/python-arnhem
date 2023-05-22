"""Basic tests for the Open Data Platform API of Arnhem."""
# pylint: disable=protected-access
import asyncio
from unittest.mock import patch

import pytest
from aiohttp import ClientError, ClientResponse, ClientSession
from aresponses import Response, ResponsesMockServer

from arnhem import ODPArnhem
from arnhem.exceptions import ODPArnhemConnectionError, ODPArnhemError

from . import load_fixtures


async def test_json_request(aresponses: ResponsesMockServer) -> None:
    """Test JSON response is handled correctly."""
    aresponses.add(
        "geo.arnhem.nl",
        "/arcgis/rest/services/test",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("e6a_parking.json"),
        ),
    )
    async with ClientSession() as session:
        client = ODPArnhem(session=session)
        response = await client._request("test")
        assert response is not None
        await client.close()


async def test_internal_session(aresponses: ResponsesMockServer) -> None:
    """Test internal session is handled correctly."""
    aresponses.add(
        "geo.arnhem.nl",
        "/arcgis/rest/services/test",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("e6a_parking.json"),
        ),
    )
    async with ODPArnhem() as client:
        await client._request("test")


async def test_timeout(aresponses: ResponsesMockServer) -> None:
    """Test request timeout is handled correctly."""

    # Faking a timeout by sleeping
    async def reponse_handler(_: ClientResponse) -> Response:
        await asyncio.sleep(0.2)
        return aresponses.Response(
            body="Goodmorning!",
            text=load_fixtures("e6a_parking.json"),
        )

    aresponses.add(
        "geo.arnhem.nl",
        "/arcgis/rest/services/test",
        "GET",
        reponse_handler,
    )

    async with ClientSession() as session:
        client = ODPArnhem(session=session, request_timeout=0.1)
        with pytest.raises(ODPArnhemConnectionError):
            assert await client._request("test")


async def test_content_type(aresponses: ResponsesMockServer) -> None:
    """Test request content type error is handled correctly."""
    aresponses.add(
        "geo.arnhem.nl",
        "/arcgis/rest/services/test",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "blabla/blabla"},
        ),
    )

    async with ClientSession() as session:
        client = ODPArnhem(session=session)
        with pytest.raises(ODPArnhemError):
            assert await client._request("test")


async def test_client_error() -> None:
    """Test request client error is handled correctly."""
    async with ClientSession() as session:
        client = ODPArnhem(session=session)
        with patch.object(
            session,
            "request",
            side_effect=ClientError,
        ), pytest.raises(ODPArnhemConnectionError):
            assert await client._request("test")
